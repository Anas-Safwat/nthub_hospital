from odoo import models, fields, api, _


class HospitalReceptionist(models.Model):
    _inherit = 'hr.employee'
    desk_location = fields.Char(string='Desk Location')
    clinic_id = fields.Many2one(comodel_name='hospital.clinic', string='Clinic', ondelete='restrict')