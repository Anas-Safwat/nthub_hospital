from datetime import timedelta
from odoo import models, fields, api

class HospitalVisit(models.Model):
    _name = 'hospital.visit'
    _description = 'Patient Visit'

    patient_id = fields.Many2one('hospital.patient', string="Patient", required=True)
    doctor_id = fields.Many2one('hr.employee', string="Doctor", required=True)
    visit_date = fields.Date(string="Visit Date", default=fields.Date.context_today)
    clinic_id = fields.Many2one('hospital.clinic', string="Clinic")
    appointment_id = fields.Many2one('hospital.appointment', string="Appointment", required=False)
    
    visit_type = fields.Selection([
        ('first_visit', 'First Visit'), # صلحتلك الـ typo بتاع Firist
        ('follow_up', 'Follow Up'),
        ('consultation', 'Consultation'),
    ], string="Visit Type", compute='_compute_visit_type', store=True, readonly=False)

    @api.model
    def _determine_visit_type(self, patient_id, doctor_id, target_date, exclude_visit_id=False):
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
                    ('doctor_id.specialization_id', '=', doctor.specialization_id.id)
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