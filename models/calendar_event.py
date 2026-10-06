from odoo import models, fields, api

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    patient_id = fields.Many2one('hospital.patient', string='Patient')
    doctor_id = fields.Many2one('hr.employee', string='Doctor', domain="[('employment_type', '=', 'doctor')]")
    department_id = fields.Many2one('hr.department', string='Department')
    chief_complaint = fields.Text(string='Chief Complaint')
    
    visit_id = fields.Many2one('hospital.visit', string='Patient Visit', readonly=True)
    state = fields.Selection([
        ('draft', 'Unconfirmed'),
        ('scheduled', 'Scheduled'),
        ('arrived', 'Arrived'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')

    def action_mark_arrived(self):
        for record in self:
            visit = self.env['hospital.visit'].create({
                'patient_id': record.patient_id.id,
                'doctor_id': record.doctor_id.id,
                'department_id': record.department_id.id,
                'appointment_id': record.id,
                'state': 'draft', # Initial state for a new visit
            })
            
            record.write({
                'state': 'arrived',
                'visit_id': visit.id
            })
