from odoo import models, fields, api, _


class HospitalDoctor(models.Model):
    _inherit = 'hr.employee'
    
    license_no = fields.Char(string='Licence Number')
    consultation_fee = fields.Float(string='Consultation Fee')
    specialization_id = fields.Many2one(comodel_name='hospital.specialization', string='Specialization', ondelete='restrict')
    clinic_ids = fields.Many2many(comodel_name='hospital.clinic', relation='doctor_clinic_rel', column1='doctor_id', column2='clinic_id')