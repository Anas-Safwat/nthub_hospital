from odoo import models, fields, api, _


class HospitalDisease(models.Model):
    _name = 'hospital.disease'
    
    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    disease_type = fields.Selection([
        ('infectious','Infectious'),
        ('deficiency','Deficiency'),
        ('hereditary','Hereditary'),
        ('physiological','Physiological')
    ],
        string='Disease Type')
    