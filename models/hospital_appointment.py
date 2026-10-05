from odoo import models, fields, api, _


class HospitalAppointment(models.Model):
    _name = 'hospital.appointment'
    
    patient_id = fields.Many2one(comodel_name='hospital.patient', string='Patient', ondelete='restrict', required=True)
    doctor_id = fields.Many2one(comodel_name='hr.employee', domain=[('employement_type', '=', 'doctor')], string='Doctor', ondelete='restrict', required=True)
    clinic_id = fields.Many2one(comodel_name='hospital.clinic', string='Clinic', ondelete='restrict', required=True)
    receptionist_id = fields.Many2one(comodel_name='hr.employee', domain=[('employement_type', '=', 'receptionist')], string='Receptionist', ondelete='restrict', help='Who registered it?')
    
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