from odoo import models, fields, api, _


class HospitalSpecialization(models.Model):
    _name = 'hospital.specialization'
    
    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    description = fields.Char(string='Description')
    doctor_ids = fields.One2many(comodel_name='hr.employee', inverse_name='specialization_id', string='Doctors', domain="[('employement_type', '=', 'doctor')]")
    nurse_ids = fields.One2many(comodel_name='hr.employee', inverse_name='specialization_id', string='Nurses', domain="[('employement_type', '=', 'nurse')]")
    