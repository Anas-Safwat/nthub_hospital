from odoo import models, fields, api, _


class HospitalVitalSigns(models.Model):
    _name = 'hospital.vital.signs'
    
    appointment_id = fields.Many2one(comodel_name='hospital.appointment', string='Appointment', required=True)
    patient_id = fields.Many2one(comodel_name='hospital.patient', string='Patient', help='Related field')
    nurse_id = fields.Many2one(comodel_name='hospital.nurse', string='Nurse', help='Who recorded')
    blood_pressure_systolic = fields.Integer(string='Blood Pressure Systolic', help='mmHg')
    blood_pressure_diastolic = fields.Integer(string='Blood Pressure Diastolic', help='mmHg')
    temperature	= fields.Float(string='Temperature', help='°C')
    pulse_rate = fields.Integer(string='Pulse Rate', help='bpm')
    respiratory_rate = fields.Integer(string='Respiratory Rate', help='breaths/min')
    weight	= fields.Float(string='Weight', help='kg')
    height	= fields.Float(string='Height', help='cm')
    spo2 = fields.Float(string='SpO2', help='%')
    recorded_at	= fields.Datetime(string='Recorded At', help='Auto-set')
    notes = fields.Text(string='Notes')