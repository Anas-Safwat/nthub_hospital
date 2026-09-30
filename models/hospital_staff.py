from odoo import models, fields, api, _


class HospitalStaff(models.AbstractModel):
    _inherit = ['hr.employee']
    
    staff_id = fields.Char(string='Staff ID')
    hire_date = fields.Date(string='Hire Date')
    employement_type = fields.Selection([
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('manager','Manager'),
        ('receptionist','Receptionist')
    ],
    string='Employement Type')
    is_active_staff = fields.Boolean(string='Is Active')
    
    