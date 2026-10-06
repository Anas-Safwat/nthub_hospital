from odoo import models, fields

class HospitalVisit(models.Model):
    _name = 'hospital.visit'
    _description = 'Patient Clinical Visit'

    name = fields.Char(string='Visit Reference', default='New', readonly=True)
    
    appointment_id = fields.Many2one('calendar.event', string='Related Appointment', readonly=True)
    
    patient_id = fields.Many2one('res.partner', string='Patient', required=True)
    doctor_id = fields.Many2one('hr.employee', string='Doctor')
    department_id = fields.Many2one('hr.department', string='Department')

    weight = fields.Float(string='Weight (kg)')
    blood_pressure = fields.Char(string='Blood Pressure')
    diagnosis = fields.Text(string='Diagnosis')
    
    state = fields.Selection([
        ('draft', 'Triage'),
        ('in_progress', 'With Doctor'),
        ('done', 'Completed')
    ], string='Status', default='draft')
