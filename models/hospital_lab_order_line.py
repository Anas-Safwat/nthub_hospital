from odoo import models, fields

class HospitalLabOrderLine(models.Model):
    _name = "hospital.lab.order.line"
    _description = "Lab Order Line"

    lab_order_id = fields.Many2one(comodel_name="hospital.lab.order", string="Lab Order", required=True, ondelete="cascade", help="Parent")
    lab_test_id = fields.Many2one(comodel_name="hospital.lab.test", string="Lab Test", help="Which test")
    result_ids = fields.One2many(comodel_name="hospital.lab.test.result", inverse_name="lab_order_line_id", string="Test Results", help="Result parameters, one per parameter")
    status = fields.Selection(selection=[('pending', 'Pending'), ('completed', 'Completed')], string="Status", default="pending", help="pending → completed")
    completed_date = fields.Datetime(string="Completed Date")