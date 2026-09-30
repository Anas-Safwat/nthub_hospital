from odoo import models, fields, api, _


class HospitalLabTest(models.Model):
    _name = 'hospital.lab.test'
    
    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    cost = fields.Char(string='Cost')
    #department_id
    description = fields.Text(string='Description')
    turnaround_time = fields.Date(string='Turnaround Time')