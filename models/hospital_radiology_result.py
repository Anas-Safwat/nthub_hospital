from odoo import models, fields

class HospitalRadiologyResult(models.Model):
    _name = "hospital.radiology.result"
    _description = "Radiology Result"

    radiology_order_id = fields.Many2one(comodel_name="hospital.radiology.order", string="Radiology Order", required=True, ondelete="cascade", help="Parent order")
    result_report = fields.Html(string="Result Report", help="Radiologist's detailed report")
    result_attachments = fields.Many2many(comodel_name="ir.attachment", string="Attachments", help="Uploaded images / scans")
    impression = fields.Text(string="Impression", help="Summary impression")
    reported_by = fields.Many2one(comodel_name="hr.employee", domain=[('employement_type', '=', 'doctor')], string="Reported By", help="Radiologist who wrote the report")
    reported_date = fields.Datetime(string="Reported Date", help="When the report was finalized")