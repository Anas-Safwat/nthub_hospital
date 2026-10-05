from odoo import models, fields, api, _


class HospitalPatient(models.Model):
    _name = 'hospital.patient'
    _inherits = {'res.partner' : 'partner_id'}
    
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    date_of_birth = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male','Male'),
        ('female','Female')
    ],
        string='Gender')
    blood_type = fields.Selection([
        ('A+','A+'),
        ('A-','A-'),
        ('B+','B+'),
        ('B-','B-'),
        ('AB+','AB+'),
        ('AB-','AB-'),
        ('O+','O+'),
        ('O-','O-'),
    ],
        string='Blood Type')
    allergies = fields.Text(string='Allergies')
