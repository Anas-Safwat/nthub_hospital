from odoo import models, fields, api, _


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'
    
    clinic_id = fields.Many2one(comodel_name='hospital.clinic', string='Clinic')
    