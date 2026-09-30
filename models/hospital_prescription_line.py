from odoo import fields, models


class HospitalPrescriptionLine(models.Model):
    _name = "hospital.prescription.line"

    prescription_id = fields.Many2one(comodel_name="hospital.prescription", string="Prescription", required=True, ondelete="cascade", help="Parent")
    medicine_id = fields.Many2one(comodel_name="hospital.medicine", string="Medicine", required=True, ondelete="restrict", help="Which medicine")
    dosage = fields.Char(string="Dosage", help='e.g., "500mg"',)
    frequency = fields.Char(string="Frequency", help='e.g., "3 times/day"',)
    duration = fields.Char(string="Duration", help='e.g., "7 days"',)
    quantity = fields.Float(string="Quantity", default=1.0, help="Total quantity")
    instructions = fields.Text(string="Instructions", help="Special instructions")
