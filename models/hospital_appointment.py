from odoo import models, fields, api, _


class HospitalAppointment(models.Model):
    _name = 'hospital.appointment'
    
    patient_id = fields.Many2one(comodel_name='hospital.patient', string='Patient', ondelete='set null', required=True)
    doctor_id = fields.Many2one(comodel_name='hospital.doctor', string='Doctor', ondelete='set null', required=True)
    clinic_id = fields.Many2one(comodel_name='hospital.clinic', string='Clinic', ondelete='set null', required=True)
    receptionist_id = fields.Many2one(comodel_name='hospital.receptionist', string='Receptionist', ondelete='set null', help='Who registered it?')
    
    is_walkin = fields.Boolean(string='Is Walkin', help='Walk-in patient flag')
    appointment_date = fields.Date(string='Appointment Date', help='Selected by patient')
    appointment_time = fields.Float(string='Appointment Time', help='Time slot')
    state = fields.Selection([
        ('draft','Draft'),
        ('confirmed','Confirmed'),
        ('in_progress','In Progress'),
        ('completed','Completed'),
        ('cancelled','Cancelled')
    ],
        string='Appointment State', help='draft → confirmed → in_progress → completed → cancelled')
    notes = fields.Text(string='Notes', help='Additional Notes')