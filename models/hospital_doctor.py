from odoo import models, fields, api, _


class HospitalDoctor(models.Model):
    _inherit = 'hr.employee'

    license_no = fields.Char(string='Licence Number')
    consultation_fee = fields.Float(string='Consultation Fee')
    specialization_id = fields.Many2one(comodel_name='hospital.specialization', string='Specialization', ondelete='restrict')
    clinic_ids = fields.Many2many(comodel_name='hospital.clinic', relation='doctor_clinic_rel', column1='doctor_id', column2='clinic_id')
    attendance_ids = fields.One2many(related='resource_calendar_id.attendance_ids', store=False, readonly=False, string='Working Days & Times')
    appointment_type_ids = fields.One2many(
        comodel_name='appointment.type',
        inverse_name='doctor_id',
        string='Appointment Types',
    )
    appointment_type_count = fields.Integer(
        string='Appointment Types',
        compute='_compute_appointment_type_count',
    )

    @api.depends('appointment_type_ids')
    def _compute_appointment_type_count(self):
        for doctor in self:
            doctor.appointment_type_count = len(doctor.appointment_type_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_doctor = vals.get('employment_type') == 'doctor' or self.env.context.get('default_employment_type') == 'doctor'
            if is_doctor and not vals.get('user_id'):
                name = vals.get('name') or _('Doctor')
                work_email = vals.get('work_email') or ''
                login = work_email.strip() if work_email else ''

                # Generate a fallback login if no work email is provided
                if not login:
                    sanitized = name.lower().replace('dr.', '').strip().replace(' ', '.')
                    login = f"{sanitized}@hospital.local"

                # Check if a user with this login already exists
                existing_user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
                if existing_user:
                    vals['user_id'] = existing_user.id
                else:
                    new_user = self.env['res.users'].sudo().with_context(no_reset_password=True).create({
                        'name': name,
                        'login': login,
                        'email': work_email or login,
                        'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
                    })
                    vals['user_id'] = new_user.id

        records = super().create(vals_list)
        # Automatically create/sync appointment types when doctor is created
        for doctor in records.filtered(lambda d: d.employment_type == 'doctor'):
            doctor._sync_or_create_appointment_types()

        return records

    def write(self, vals):
        res = super().write(vals)
        # Automatically sync or create appointment types whenever doctor changes are saved
        for doctor in self.filtered(lambda d: d.employment_type == 'doctor'):
            doctor._sync_or_create_appointment_types()
        return res

    def _sync_or_create_appointment_types(self):
        """Create or sync appointment types automatically (per clinic if doctor has clinics)."""
        for doctor in self:
            staff_user = doctor.user_id or self.env.user
            clinics = doctor.clinic_ids
            created_or_synced_ids = []

            if clinics:
                for clinic in clinics:
                    existing = doctor.appointment_type_ids.filtered(lambda a: a.clinic_id == clinic)[:1]
                    if existing:
                        existing._sync_doctor_schedule()
                        created_or_synced_ids.append(existing.id)
                    else:
                        appt_type = self.env['appointment.type'].create({
                            'name': _('%(doctor)s - %(clinic)s', doctor=doctor.name, clinic=clinic.name),
                            'doctor_id': doctor.id,
                            'clinic_id': clinic.id,
                            'appointment_duration': 0.5,
                            'slot_creation_interval': 0.5,
                            'schedule_based_on': 'users',
                            'work_hours_activated': True,
                            'category': 'recurring',
                            'staff_user_ids': [(6, 0, staff_user.ids)],
                            'max_schedule_days': 30,
                        })
                        appt_type._sync_doctor_schedule()
                        created_or_synced_ids.append(appt_type.id)
            else:
                existing = doctor.appointment_type_ids[:1]
                if existing:
                    existing._sync_doctor_schedule()
                    created_or_synced_ids.append(existing.id)
                else:
                    appt_type = self.env['appointment.type'].create({
                        'name': _('%s - Consultation', doctor.name),
                        'doctor_id': doctor.id,
                        'appointment_duration': 0.5,
                        'slot_creation_interval': 0.5,
                        'schedule_based_on': 'users',
                        'work_hours_activated': True,
                        'category': 'recurring',
                        'staff_user_ids': [(6, 0, staff_user.ids)],
                        'max_schedule_days': 30,
                    })
                    appt_type._sync_doctor_schedule()
                    created_or_synced_ids.append(appt_type.id)

        return created_or_synced_ids

    def action_create_appointment_type(self):
        """Manual action to sync/create appointment types and open the view."""
        self.ensure_one()
        created_or_synced_ids = self._sync_or_create_appointment_types()

        if len(created_or_synced_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Appointment Type'),
                'res_model': 'appointment.type',
                'res_id': created_or_synced_ids[0],
                'view_mode': 'form',
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointment Types'),
            'res_model': 'appointment.type',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_or_synced_ids)],
            'context': {'default_doctor_id': self.id},
            'target': 'current',
        }

    def action_view_appointment_types(self):
        """Open the appointment types linked to this doctor."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointment Types'),
            'res_model': 'appointment.type',
            'view_mode': 'list,form',
            'domain': [('doctor_id', '=', self.id)],
            'context': {'default_doctor_id': self.id},
        }
