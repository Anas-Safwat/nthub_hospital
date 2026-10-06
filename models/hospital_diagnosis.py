from odoo import models, fields, api, _


class HospitalDiagnosis(models.Model):
    _name = 'hospital.diagnosis'
    
    appointment_id = fields.Many2one(comodel_name='calendar.event', string='Appointment', required=True)
    patient_id = fields.Many2one(comodel_name='hospital.patient', string='Patient', help='Related from appointment')
    doctor_id = fields.Many2one(comodel_name='hr.employee', domain=[('employement_type', '=', 'doctor')], string='Doctor', help='Related from appointment')
    disease_id = fields.Many2one(comodel_name='hospital.disease', string='Disease', help='Diagnosed condition')

    diagnosis_notes	= fields.Html(string='Notes', help="Doctor's detailed notes")
    severity = fields.Selection([
        ('mild','Mild'),
        ('moderate','Moderate'),
        ('severe','Severe'),
        ('critical','Critical')
        ], string='Severity')
    date = fields.Date(string='Diagnosis Date', help='Date of diagnosis')