import pytz

from odoo import models, fields, api, _


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    doctor_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Doctor',
        domain=[('employment_type', '=', 'doctor')],
        help='Doctor linked to this appointment type.',
    )