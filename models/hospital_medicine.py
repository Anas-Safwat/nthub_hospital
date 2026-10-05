from odoo import fields, models


class HospitalMedicine(models.Model):
    _name = "hospital.medicine"

    name = fields.Char(string="Name")
