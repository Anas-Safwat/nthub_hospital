from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError


class HospitalAppointment(models.Model):
    _name = 'hospital.appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Patient Appointment'
    _order = 'appointment_date desc, id desc'
    _rec_name = 'display_name'

    # ── Core fields ───────────────────────────────────────────────
    patient_id = fields.Many2one('hospital.patient', string="Patient")
    patient_name = fields.Char(string="Patient Name")
    patient_phone = fields.Char(string="Patient Phone")
    doctor_id = fields.Many2one('hr.employee', string="Doctor", required=True,
                                domain="[('employment_type', '=', 'doctor')]")
    appointment_date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    @api.depends('patient_id', 'patient_name', 'appointment_date')
    def _compute_display_name(self):
        for rec in self:
            name = rec.patient_id.name or rec.patient_name or _('Walk-in')
            date_str = rec.appointment_date.strftime('%d/%m/%Y') if rec.appointment_date else ''
            rec.display_name = f"{name} - {date_str}" if date_str else name

    # Auto-computed based on doctor + date
    timetable_id = fields.Many2one(
        'hospital.timetable',
        string="Available Timetable",
        compute='_compute_timetable_id',
        store=True
    )

    # Shows only available slots for this timetable and date
    slot_id = fields.Many2one(
        'hospital.timetable.slot',
        string="Slot",
        required=True,
        domain="[('timetable_id', '=', timetable_id), ('slot_date', '=', appointment_date), ('state', '=', 'available')]"
    )

    slot_type = fields.Selection(
        related='slot_id.type',
        string="Type",
        store=True,
        readonly=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    visit_id = fields.Many2one('hospital.visit', string="Visit", readonly=True)

    visit_type = fields.Selection([
        ('first_visit', 'First Visit'),
        ('follow_up', 'Follow Up'),
        ('consultation', 'Consultation'),
    ], string="Visit Type", compute='_compute_visit_type', store=True, readonly=False)

    # ── Billing fields ────────────────────────────────────────────
    invoice_ids = fields.One2many(
        'account.move', 'appointment_id', string='Invoices',
    )
    invoice_count = fields.Integer(
        compute='_compute_invoice_data', string='Invoice Count',
    )
    total_invoiced = fields.Monetary(
        compute='_compute_invoice_data', string='Total Invoiced',
        currency_field='currency_id',
    )
    consultation_invoice_id = fields.Many2one(
        'account.move', string='Consultation Invoice',
        copy=False, readonly=True,
    )
    consultation_payment_state = fields.Selection(
        related='consultation_invoice_id.payment_state',
        string='Consultation Payment', store=True,
    )

    # ── Computed billing helpers ──────────────────────────────────
    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.amount_total_signed')
    def _compute_invoice_data(self):
        for rec in self:
            invoices = rec.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice')
            rec.invoice_count = len(invoices)
            rec.total_invoiced = sum(invoices.mapped('amount_total_signed'))

    # ── Split-settlement helpers ──────────────────────────────────
    def _get_or_create_open_invoice(self):
        """Return an existing draft customer invoice or create a new one."""
        self.ensure_one()
        draft = self.invoice_ids.filtered(
            lambda m: m.state == 'draft' and m.move_type == 'out_invoice'
        )
        if draft:
            return draft[0]

        partner = self.patient_id.partner_id
        if not partner:
            raise UserError(_('Patient "%s" has no linked partner. Save the patient first.', self.patient_id.name))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'appointment_id': self.id,
            'invoice_origin': self.display_name or '',
            'invoice_date': fields.Date.context_today(self),
        })
        return invoice

    def _append_service_to_invoice(self, product, quantity=1.0, description=False):
        """Add a service line to the open draft invoice. Return the new account.move.line."""
        self.ensure_one()
        invoice = self._get_or_create_open_invoice()

        line_vals = {
            'product_id': product.id,
            'name': description or product.name,
            'quantity': quantity,
            'price_unit': product.lst_price,
            'tax_ids': [Command.set(product.taxes_id.ids)],
        }

        invoice.write({
            'invoice_line_ids': [Command.create(line_vals)],
        })
        # Return the last-created line
        return invoice.invoice_line_ids.sorted('id', reverse=True)[0]

    # ── Smart button action ───────────────────────────────────────
    def action_view_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if self.invoice_count == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = self.invoice_ids[0].id
        else:
            action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        action['context'] = {
            'default_move_type': 'out_invoice',
            'default_appointment_id': self.id,
            'default_partner_id': self.patient_id.partner_id.id,
        }
        return action

    # ── Existing compute/onchange ─────────────────────────────────
    @api.depends('patient_id', 'doctor_id', 'appointment_date')
    def _compute_visit_type(self):
        for rec in self:
            rec.visit_type = self.env['hospital.visit']._determine_visit_type(
                rec.patient_id.id,
                rec.doctor_id.id,
                rec.appointment_date
            )

    @api.depends('doctor_id', 'appointment_date')
    def _compute_timetable_id(self):
        for rec in self:
            if rec.doctor_id and rec.appointment_date:
                timetable = self.env['hospital.timetable'].search([
                    ('doctor_id', '=', rec.doctor_id.id),
                    ('date_from', '<=', rec.appointment_date),
                    ('date_to', '>=', rec.appointment_date)
                ], limit=1)
                rec.timetable_id = timetable.id if timetable else False
            else:
                rec.timetable_id = False

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.patient_name = self.patient_id.name
            self.patient_phone = self.patient_id.phone

    @api.onchange('doctor_id', 'appointment_date')
    def _onchange_reset_slot(self):
        if self.slot_id and (
            self.slot_id.doctor_id != self.doctor_id
            or self.slot_id.slot_date != self.appointment_date
        ):
            self.slot_id = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.slot_id:
                rec.slot_id.write({
                    'state': 'booked',
                    'appointment_id': rec.id,
                })
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'cancelled':
            today = fields.Date.context_today(self)
            for rec in self:
                if rec.slot_id and rec.slot_id.slot_date >= today:
                    rec.slot_id.write({
                        'state': 'available',
                        'appointment_id': False,
                    })
        return res

    def action_cancel(self):
        """Cancel the appointment and free the slot."""
        self.write({'state': 'cancelled'})

    def action_confirm_visit(self):
        """Confirm appointment, create consultation invoice line, open a visit."""
        self.ensure_one()

        # ── Stage 1: Create consultation invoice line ─────────────
        consultation_product = self.doctor_id._get_or_create_consultation_product()
        self._append_service_to_invoice(
            consultation_product,
            description=_('Consultation – %s', self.doctor_id.name),
        )
        self.consultation_invoice_id = self._get_or_create_open_invoice()

        # ── Create the visit ──────────────────────────────────────
        visit = self.env['hospital.visit'].create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id,
            'appointment_id': self.id,
            'visit_date': self.appointment_date,
            'visit_type': self.visit_type,  # <-- هنا بياخد القيمة المحسوبة (أو اللي الريسيبشنيست عدلها)
        })
        self.write({
            'state': 'confirmed',
            'visit_id': visit.id,
        })
        