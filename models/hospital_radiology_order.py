from odoo import models, fields

class HospitalRadiologyOrder(models.Model):
    _name = "hospital.radiology.order"
    _description = "Radiology Order"

    appointment_id = fields.Many2one(comodel_name="hospital.appointment", string="Appointment", required=True, ondelete="cascade")
    doctor_id = fields.Many2one(comodel_name="hr.employee", domain=[('employement_type', '=', 'doctor')], string="Doctor", help="Who ordered")
    patient_id = fields.Many2one(comodel_name="hospital.patient", string="Patient", help="Related patient")
    radiology_service_id = fields.Many2one(comodel_name="hospital.radiology.service", string="Radiology Service", help="Which imaging service")
    result_id = fields.Many2one(comodel_name="hospital.radiology.result", string="Result", help="Result record, created when completed")
    state = fields.Selection(selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('in_progress', 'In Progress'), ('completed', 'Completed')], string="Status", default="draft", help="draft → confirmed → in_progress → completed")
    date = fields.Date(string="Date", help="Order date")
    notes = fields.Text(string="Notes")