from odoo import models, fields


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    patient_id = fields.Many2one('hospital.patient', string='Patient')
    doctor_id = fields.Many2one(
        'hr.employee', string='Doctor',
        domain="[('employment_type', '=', 'doctor')]",
    )
    department_id = fields.Many2one('hr.department', string='Department')
    chief_complaint = fields.Text(string='Chief Complaint')
    visit_id = fields.Many2one(
        'hospital.visit', string='Patient Visit', readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Unconfirmed'),
        ('scheduled', 'Scheduled'),
        ('arrived', 'Arrived'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
