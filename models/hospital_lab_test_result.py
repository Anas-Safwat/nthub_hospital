from odoo import models, fields

class HospitalLabTestResult(models.Model):
    _name = "hospital.lab.test.result"
    _description = "Lab Test Result"

    lab_order_line_id = fields.Many2one(comodel_name="hospital.lab.order.line", string="Lab Order Line", required=True, ondelete="cascade", help="Parent")
    parameter_name = fields.Char(string="Parameter Name", help="e.g., WBC, Hemoglobin, Glucose")
    result_value = fields.Char(string="Result Value", help="The actual result value")
    unit = fields.Char(string="Unit", help="Unit of measurement, e.g., mg/dL")
    normal_range = fields.Char(string="Normal Range", help="Reference range, e.g., 70–100")
    is_abnormal = fields.Boolean(string="Is Abnormal", help="Flagged if outside normal range")
    notes = fields.Text(string="Notes", help="Interpretation or remarks")