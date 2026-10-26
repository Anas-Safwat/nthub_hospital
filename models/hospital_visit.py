from datetime import timedelta
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError


class HospitalVisit(models.Model):
    _name = 'hospital.visit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Patient Visit'
    _order = 'visit_date desc, id desc'

    patient_id = fields.Many2one(
        'hospital.patient', string="Patient", required=True,
    )
    doctor_id = fields.Many2one(
        'hr.employee', string="Doctor", required=True,
        domain="[('employment_type', '=', 'doctor')]",
    )
    visit_date = fields.Date(
        string="Visit Date", default=fields.Date.context_today,
    )
    clinic_id = fields.Many2one('hospital.clinic', string="Clinic")
    appointment_id = fields.Many2one(
        'hospital.appointment', string="Appointment", readonly=True,
    )

    visit_type = fields.Selection([
        ('first_visit', 'First Visit'),
        ('follow_up', 'Follow Up'),
        ('consultation', 'Consultation'),
    ], string="Visit Type", compute='_compute_visit_type',
        store=True, readonly=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True, required=True)

    # ── Billing ───────────────────────────────────────────────────
    invoice_id = fields.Many2one(
        'account.move', string='Invoice', readonly=True, copy=False,
    )
    payment_id = fields.Many2one(
        'account.payment', string='Payment', readonly=True, copy=False,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    amount_total = fields.Monetary(
        string='Total Amount', compute='_compute_amount_total',
        store=True, currency_field='currency_id',
    )

    # ── Clinical ──────────────────────────────────────────────────
    assessment_notes = fields.Html(string='Assessment Notes')

    # ── Lines ─────────────────────────────────────────────────────
    service_line_ids = fields.One2many(
        'hospital.visit.service.line', 'visit_id', string='Services',
    )
    medicine_line_ids = fields.One2many(
        'hospital.visit.medicine.line', 'visit_id', string='Medicines',
    )

    # ── Computed ──────────────────────────────────────────────────
    @api.depends('service_line_ids.subtotal')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.service_line_ids.mapped('subtotal'))

    # ── Visit type determination ──────────────────────────────────
    @api.model
    def _determine_visit_type(self, patient_id, doctor_id, target_date,
                              exclude_visit_id=False):
        """
        Helper method to calculate visit type based on history in hospital.visit.
        Can be called from both Appointment and Visit models.
        """
        if not patient_id or not doctor_id or not target_date:
            return 'first_visit'

        cutoff_date = target_date - timedelta(days=14)

        base_domain = [
            ('patient_id', '=', patient_id),
            ('visit_date', '>=', cutoff_date),
            ('visit_date', '<=', target_date),
        ]
        if exclude_visit_id:
            base_domain.append(('id', '!=', exclude_visit_id))

        same_doctor_visit = self.search(
            base_domain + [('doctor_id', '=', doctor_id)],
            limit=1
        )
        if same_doctor_visit:
            return 'follow_up'

        doctor = self.env['hr.employee'].browse(doctor_id)

        if doctor.specialization_id:
            same_specialty_other_doctor_visit = self.search(
                base_domain + [
                    ('doctor_id', '!=', doctor_id),
                    ('doctor_id.specialization_id', '=',
                     doctor.specialization_id.id)
                ],
                limit=1
            )
            if same_specialty_other_doctor_visit:
                return 'consultation'

        return 'first_visit'

    @api.depends('patient_id', 'doctor_id', 'visit_date')
    def _compute_visit_type(self):
        for rec in self:
            rec.visit_type = self._determine_visit_type(
                rec.patient_id.id,
                rec.doctor_id.id,
                rec.visit_date,
                exclude_visit_id=rec._origin.id
            )

    # ── Actions ───────────────────────────────────────────────────
    def action_register_payment(self):
        """Create and post a pre-visit payment."""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice linked to this visit."))

        journal = self.env['account.journal'].search(
            [('type', 'in', ['bank', 'cash']),
             ('company_id', '=', self.env.company.id)],
            limit=1,
        )
        if not journal:
            raise UserError(_(
                "No bank or cash journal found. "
                "Please configure one first."
            ))

        amount = self.amount_total
        if amount <= 0:
            raise UserError(_(
                "Payment amount must be greater than zero."
            ))

        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.patient_id.partner_id.id,
            'amount': amount,
            'journal_id': journal.id,
            'memo': _('Pre-visit payment – %s',
                     self.appointment_id.display_name or ''),
        })
        payment.action_post()
        payment.action_validate()
        self.write({
            'payment_id': payment.id,
            'state': 'paid',
        })

    def action_start_visit(self):
        """Transition the visit to in_progress after verifying payment."""
        self.ensure_one()
        if not self.payment_id or self.payment_id.state != 'paid':
            raise ValidationError(_(
                "The patient must pay the consultation fee before starting "
                "the visit. Please register a payment first."
            ))
        self.state = 'in_progress'

    def action_checkout(self):
        """Push unlinked service lines to the draft invoice, post it,
        and close the visit."""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_(
                "Only visits that are in progress can be checked out."
            ))
        if not self.invoice_id:
            raise UserError(_("No invoice linked to this visit."))
        if self.invoice_id.state != 'draft':
            raise UserError(_(
                "The invoice is no longer in draft state "
                "and cannot be modified."
            ))

        # Push unlinked service lines to the draft invoice
        for line in self.service_line_ids:
            if line.invoice_line_id:
                continue  # already on invoice — skip
            self.invoice_id.write({
                'invoice_line_ids': [Command.create({
                    'product_id': line.product_id.id,
                    'name': line.name or line.product_id.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                })],
            })
            # Link the newly created invoice line back
            new_aml = self.invoice_id.invoice_line_ids.filtered(
                lambda l: l.product_id
            ).sorted('id', reverse=True)[0]
            line.invoice_line_id = new_aml.id

        # Post the invoice and close the visit
        self.invoice_id.action_post()
        self.state = 'done'

    # ── Smart-button helpers ──────────────────────────────────────
    def action_view_invoice(self):
        """Open the linked invoice."""
        self.ensure_one()
        if not self.invoice_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_view_payment(self):
        """Open the linked payment."""
        self.ensure_one()
        if not self.payment_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }