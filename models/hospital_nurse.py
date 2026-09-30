from odoo import models, fields, api, _


class HospitalNurse(models.Model):
    _name = 'hospital.nurse'
    _inherit = ['hr.employee']
    nursing_level = fields.Selection([
        ('certified','Certified'),
        ('licensed','Licensed'),
        ('registered','Registered'),
        ('advanced','Advanced'),
        ('doctoral','Doctoral')
    ],
        string='Nursing Level')
    certification = fields.Char(string='Certification')
    specialization_id = fields.Many2one(comodel_name='hospital.specialization', string='Specialization', ondelete='set null')
