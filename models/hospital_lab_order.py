from odoo import models, fields

class HospitalLabOrder(models.Model):
    _name = "hospital.lab.order"
    _description = "Lab Order"

    appointment_id = fields.Many2one(comodel_name="calendar.event", string="Appointment", required=True, ondelete="cascade")
    doctor_id = fields.Many2one(comodel_name="hr.employee", domain=[('employement_type', '=', 'doctor')], string="Doctor", help="Who ordered")
    patient_id = fields.Many2one(comodel_name="hospital.patient", string="Patient", help="Related patient")
    lab_order_line_ids = fields.One2many(comodel_name="hospital.lab.order.line", inverse_name="lab_order_id", string="Lab Order Lines", help="Test lines")
    state = fields.Selection(selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('sample_collected', 'Sample Collected'), ('in_progress', 'In Progress'), ('completed', 'Completed')], string="Status", default="draft", help="draft → confirmed → sample_collected → in_progress → completed")
    date = fields.Date(string="Date", help="Order date")
    notes = fields.Text(string="Notes")