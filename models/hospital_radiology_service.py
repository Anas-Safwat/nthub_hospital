from odoo import models, fields, api, _


class HospitalRadiologyService(models.Model):
    _name = 'hospital.radiology.service'
    
    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    cost = fields.Char(string='Cost')
    #department_id
    description = fields.Text(string='Description')