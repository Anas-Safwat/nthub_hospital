from odoo import models, fields, api, _


class HospitalStaff(models.Model):
    
    _inherit = 'hr.employee'
    staff_id = fields.Char(string='Staff ID')
    hire_date = fields.Date(string='Hire Date')
    is_active_staff = fields.Boolean(string='Is Active')
    employment_type = fields.Selection([
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('manager','Manager'),
        ('receptionist','Receptionist')
    ],
    string='Employement Type')