from odoo import models, fields, api, _


class HrDepartment(models.Model):
    _inherit = 'hr.department'
    
    code = fields.Char(string='Code')
    is_clinical = fields.Boolean(string='Is Clinical')
    location = fields.Char(string='Location')