from odoo import models, fields, api, _


class HospitalAppointment(models.Model):
    _name = 'hospital.appointment'
    _description = 'Patient Appointment'
    _order = 'appointment_date desc, id desc'

    patient_id = fields.Many2one('hospital.patient', string="Patient", required=True)
    doctor_id = fields.Many2one('hr.employee', string="Doctor", required=True,
                                domain="[('employment_type', '=', 'doctor')]")
    appointment_date = fields.Date(string="Date", required=True, default=fields.Date.context_today)

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

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed / Visit Opened'),
        ('cancelled', 'Cancelled')
    ], default='draft')

    visit_id = fields.Many2one('hospital.visit', string="Visit", readonly=True)

    visit_type = fields.Selection([
        ('first_visit', 'First Visit'),
        ('follow_up', 'Follow Up'),
        ('consultation', 'Consultation'),
    ], string="Visit Type", compute='_compute_visit_type', store=True, readonly=False)

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

    @api.onchange('doctor_id', 'appointment_date')
    def _onchange_reset_slot(self):
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
            for rec in self:
                if rec.slot_id:
                    rec.slot_id.write({
                        'state': 'available',
                        'appointment_id': False,
                    })
        return res

    def action_cancel(self):
        """Cancel the appointment and free the slot."""
        self.write({'state': 'cancelled'})

    def action_confirm_visit(self):
        """Confirm appointment and open a visit for the patient."""
        self.ensure_one()
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
        