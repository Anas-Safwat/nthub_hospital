from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError


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
    doctor_id = fields.Many2one(
        'hr.employee', string="Doctor", required=True,
        domain="[('employment_type', '=', 'doctor')]",
    )
    appointment_date = fields.Date(
        string="Date", required=True,
        default=fields.Date.context_today,
    )
    display_name = fields.Char(
        compute='_compute_display_name', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    @api.depends('patient_id', 'patient_name', 'appointment_date')
    def _compute_display_name(self):
        for rec in self:
            name = rec.patient_id.name or rec.patient_name or _('Walk-in')
            date_str = (rec.appointment_date.strftime('%d/%m/%Y')
                        if rec.appointment_date else '')
            rec.display_name = (f"{name} - {date_str}"
                                if date_str else name)

    # Auto-computed based on doctor + date
    timetable_id = fields.Many2one(
        'hospital.timetable',
        string="Available Timetable",
        compute='_compute_timetable_id',
        store=True,
    )

    # Shows only available slots for this timetable and date
    slot_id = fields.Many2one(
        'hospital.timetable.slot',
        string="Slot",
        required=True,
        domain=("[('timetable_id', '=', timetable_id),"
                " ('slot_date', '=', appointment_date),"
                " ('state', '=', 'available')]"),
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
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    visit_id = fields.Many2one(
        'hospital.visit', string="Visit", readonly=True,
    )

    visit_type = fields.Selection([
        ('first_visit', 'First Visit'),
        ('follow_up', 'Follow Up'),
        ('consultation', 'Consultation'),
    ], string="Visit Type", compute='_compute_visit_type',
        store=True, readonly=False)

    # ── Billing ───────────────────────────────────────────────────
    invoice_id = fields.Many2one(
        'account.move', string='Invoice',
        copy=False, readonly=True,
    )

    # ── Compute / Onchange ────────────────────────────────────────
    @api.depends('patient_id', 'doctor_id', 'appointment_date')
    def _compute_visit_type(self):
        for rec in self:
            rec.visit_type = self.env['hospital.visit']._determine_visit_type(
                rec.patient_id.id,
                rec.doctor_id.id,
                rec.appointment_date,
            )

    @api.depends('doctor_id', 'appointment_date')
    def _compute_timetable_id(self):
        for rec in self:
            if rec.doctor_id and rec.appointment_date:
                timetable = self.env['hospital.timetable'].search([
                    ('doctor_id', '=', rec.doctor_id.id),
                    ('date_from', '<=', rec.appointment_date),
                    ('date_to', '>=', rec.appointment_date),
                ], limit=1)
                rec.timetable_id = (timetable.id if timetable
                                    else False)
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

    # ── Constraints ───────────────────────────────────────────────
    @api.constrains('patient_id', 'doctor_id', 'appointment_date')
    def _check_unique_patient_doctor_per_day(self):
        for rec in self:
            if not rec.patient_id or not rec.doctor_id or not rec.appointment_date:
                continue
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('patient_id', '=', rec.patient_id.id),
                ('doctor_id', '=', rec.doctor_id.id),
                ('appointment_date', '=', rec.appointment_date),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    "Patient '%(patient)s' already has an appointment with "
                    "Dr. %(doctor)s on %(date)s.",
                    patient=rec.patient_id.name,
                    doctor=rec.doctor_id.name,
                    date=rec.appointment_date.strftime('%d/%m/%Y'),
                ))

    # ── CRUD overrides ────────────────────────────────────────────
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

    # ── Actions ───────────────────────────────────────────────────
    def action_cancel(self):
        """Cancel the appointment and free the slot."""
        self.write({'state': 'cancelled'})

    def action_confirm(self):
        """Confirm appointment: create draft invoice, visit with
        initial service line, and link everything together."""
        self.ensure_one()

        if not self.patient_id:
            raise UserError(_(
                "Please select a patient before confirming."
            ))
        if not self.patient_id.partner_id:
            raise UserError(_(
                "Patient '%s' has no linked partner. "
                "Please save the patient first.",
                self.patient_id.name,
            ))
        if not self.visit_type:
            raise UserError(_(
                "Please select a visit type before confirming."
            ))

        # Resolve the consultation service from the doctor's services
        service = self.doctor_id._get_service(
            service_xmlid='nthub_hospital.hospital_service_consultation',
            service_name='Consultation',
        )
        if self.slot_type == 'operation':
            service = self.doctor_id._get_service(
                service_xmlid='nthub_hospital.hospital_service_operation',
                service_name='Operation',
            )
        else:
            service = self.doctor_id._get_service(
                service_xmlid='nthub_hospital.hospital_service_consultation',
                service_name='Consultation',
            )
        product = service.product_id
        price = product.lst_price or self.doctor_id.consultation_fee
        # 1. Create draft invoice with the initial service line
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.patient_id.partner_id.id,
            'invoice_date': self.appointment_date,
            'invoice_origin': self.display_name or '',
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
                'name': product.name,
                'quantity': 1.0,
                'price_unit': product.lst_price,
            })],
        })

        # 2. Retrieve the created invoice line
        invoice_line = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id
        )[0]

        # 3. Create the visit with initial service line
        #    linked to the invoice line
        visit = self.env['hospital.visit'].create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id,
            'appointment_id': self.id,
            'visit_date': self.appointment_date,
            'visit_type': self.visit_type,
            'invoice_id': invoice.id,
            'state': 'draft',
            'service_line_ids': [Command.create({
                'product_id': product.id,
                'name': product.name,
                'quantity': 1.0,
                'price_unit': product.lst_price,
                'invoice_line_id': invoice_line.id,
            })],
        })

        # 4. Link visit and invoice back to appointment
        self.write({
            'state': 'confirmed',
            'visit_id': visit.id,
            'invoice_id': invoice.id,
        })