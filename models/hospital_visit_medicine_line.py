from odoo import models, fields


class HospitalVisitMedicineLine(models.Model):
    _name = 'hospital.visit.medicine.line'
    _description = 'Visit Medicine Line'

    visit_id = fields.Many2one(
        'hospital.visit', string='Visit',
        required=True, ondelete='cascade',
    )
    medicine_id = fields.Many2one(
        'hospital.medicine', string='Medicine', required=True,
    )
    dosage = fields.Char(string='Dosage', help='e.g., "500mg"')
    frequency = fields.Char(string='Frequency', help='e.g., "3 times/day"')
    duration = fields.Char(string='Duration', help='e.g., "7 days"')
    quantity = fields.Float(string='Quantity', default=1.0)
    instructions = fields.Text(string='Instructions')
