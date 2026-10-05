from odoo import fields, models


class HospitalPrescription(models.Model):
    _name = "hospital.prescription"
    _description = "Hospital Prescription"

    appointment_id = fields.Many2one(comodel_name="hospital.appointment", string="Appointment", required=True, ondelete="restrict",)
    doctor_id = fields.Many2one(comodel_name="hr.employee", domain=[('employement_type', '=', 'doctor')], string="Doctor", related="appointment_id.doctor_id", store=True, readonly=True,)
    patient_id = fields.Many2one(comodel_name="hospital.patient", string="Patient", related="appointment_id.patient_id", store=True, readonly=True,)
    prescription_line_ids = fields.One2many(comodel_name="hospital.prescription.line", inverse_name="prescription_id", string="Prescription Lines", help="Medicine lines")
    state = fields.Selection([
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("dispensed", "Dispensed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status", default="draft",required=True, help="draft → confirmed → dispensed → cancelled")
    date = fields.Date(string="Date",default=fields.Date.context_today,required=True, help="Auto-set")
    notes = fields.Text(string="Notes",)