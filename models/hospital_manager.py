from odoo import models, fields, api, _


class HospitalManager(models.Model):
    _name = 'hospital.manager'
    _inherit = ['hr.employee']