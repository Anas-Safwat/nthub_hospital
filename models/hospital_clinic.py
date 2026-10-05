from odoo import models, fields, api, _


class HospitalClinic(models.Model):
    _name = 'hospital.clinic'
    
    name = fields.Char(string='Name')
    department_id = fields.Many2one(comodel_name='hr.department', string='Department', ondelete='restrict')
    location = fields.Char(string='Location')
    capacity = fields.Integer(string='Capacity')
    is_active = fields.Boolean(string='Is Active') 
    