from odoo import models, fields, api, _


class HospitalDoctor(models.Model):
    _inherit = 'hr.employee'

    license_no = fields.Char(string='Licence Number')
    consultation_fee = fields.Float(string='Consultation Fee')
    specialization_id = fields.Many2one(comodel_name='hospital.specialization', string='Specialization', ondelete='restrict')

    attendance_ids = fields.One2many(
        related='resource_calendar_id.attendance_ids',
        store=False,
        readonly=False,
        string='Working Days & Times',
    )
    
    clinic_ids = fields.Many2many(comodel_name='hospital.clinic',relation='doctor_clinic_rel',column1='doctor_id',column2='clinic_id',string='Clinics',)
    resource_calendar_id = fields.Many2one('resource.calendar', string="Working Schedule", required=True, ondelete='cascade')
    timetable_ids = fields.One2many('hospital.timetable', 'doctor_id', string="Timetables")

    def _create_personal_calendar(self, name):
        """Create a dedicated resource.calendar for this doctor."""
        return self.env['resource.calendar'].create({
            'name': _('Schedule – %s', name),
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_doctor = (
                vals.get('employment_type') == 'doctor'
                or self.env.context.get('default_employment_type') == 'doctor'
            )
            if not is_doctor:
                continue

            # ── Auto-create portal user ──────────────────────────────
            if not vals.get('user_id'):
                name = vals.get('name') or _('Doctor')
                work_email = vals.get('work_email') or ''
                login = work_email.strip() if work_email else ''

                if not login:
                    sanitized = name.lower().replace('dr.', '').strip().replace(' ', '.')
                    login = f"{sanitized}@hospital.local"

                existing_user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
                if existing_user:
                    vals['user_id'] = existing_user.id
                else:
                    new_user = self.env['res.users'].sudo().with_context(no_reset_password=True).create({
                        'name': vals.get('name') or _('Doctor'),
                        'login': login,
                        'email': work_email or login,
                        'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
                    })
                    vals['user_id'] = new_user.id

            # ── Personal calendar: always give the doctor their own ──
            doctor_name = vals.get('name') or _('Doctor')
            if vals.get('resource_calendar_id'):
                # Clone the selected calendar so this doctor gets a personal copy
                source_cal = self.env['resource.calendar'].browse(vals['resource_calendar_id'])
                personal_cal = source_cal.copy({'name': _('Schedule – %s', doctor_name)})
                vals['resource_calendar_id'] = personal_cal.id
            else:
                # Create a blank personal calendar
                personal_cal = self._create_personal_calendar(doctor_name)
                vals['resource_calendar_id'] = personal_cal.id

        return super().create(vals_list)

    