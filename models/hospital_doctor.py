from odoo import models, fields, api, _


class HospitalDoctor(models.Model):
    _inherit = 'hr.employee'

    license_no = fields.Char(string='Licence Number')
    consultation_fee = fields.Float(string='Consultation Fee')
    specialization_id = fields.Many2one(comodel_name='hospital.specialization', string='Specialization', ondelete='restrict')

    # ── Computed from Schedule attendance_ids ─────────────────────────────
    clinic_ids = fields.Many2many(
        comodel_name='hospital.clinic',
        relation='doctor_clinic_rel',
        column1='doctor_id',
        column2='clinic_id',
        compute='_compute_clinic_ids',
        store=True,
        string='Clinics',
        help='Automatically computed from the Schedule: lists every clinic that has at least one time slot.',
    )

    attendance_ids = fields.One2many(
        related='resource_calendar_id.attendance_ids',
        store=False,
        readonly=False,
        string='Working Days & Times',
    )

    # ── Consultation Duration (stored here, synced to appointment types) ──
    consultation_duration = fields.Float(
        string='Consultation Duration (hours)',
        default=0.5,
        help='Duration (in hours) for each appointment slot. Synced automatically to all linked Appointment Types.',
    )

    # ── Appointment Types (one per clinic, auto-managed) ──────────────────
    appointment_type_ids = fields.One2many(
        comodel_name='appointment.type',
        inverse_name='doctor_id',
        string='Appointment Types',
    )

    # ── Booked Appointments smart button ─────────────────────────────────
    appointment_count = fields.Integer(
        string='Appointments',
        compute='_compute_appointment_count',
    )

    # ─────────────────────────────────────────────────────────────────────
    # Compute: clinic_ids from schedule
    # ─────────────────────────────────────────────────────────────────────

    @api.depends('attendance_ids', 'attendance_ids.clinic_id', 'resource_calendar_id')
    def _compute_clinic_ids(self):
        for doctor in self:
            clinic_ids = doctor.attendance_ids.mapped('clinic_id').filtered(lambda c: c.id)
            doctor.clinic_ids = clinic_ids

    # ─────────────────────────────────────────────────────────────────────
    # Compute: booked appointments count
    # ─────────────────────────────────────────────────────────────────────

    @api.depends('appointment_type_ids', 'appointment_type_ids.meeting_ids')
    def _compute_appointment_count(self):
        for doctor in self:
            doctor.appointment_count = sum(
                len(apt.meeting_ids) for apt in doctor.appointment_type_ids
            )

    # ─────────────────────────────────────────────────────────────────────
    # Create: do NOT auto-create appointment types
    # ─────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_doctor = (
                vals.get('employment_type') == 'doctor'
                or self.env.context.get('default_employment_type') == 'doctor'
            )
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

        # No automatic appointment type creation on doctor creation (req #1)
        return super().create(vals_list)

    # ─────────────────────────────────────────────────────────────────────
    # Write: sync appointment types when schedule/duration changes
    # ─────────────────────────────────────────────────────────────────────

    def write(self, vals):
        res = super().write(vals)
        schedule_related = {'resource_calendar_id', 'attendance_ids', 'name', 'user_id'}
        if schedule_related.intersection(vals.keys()):
            for doctor in self.filtered(lambda d: d.employment_type == 'doctor'):
                doctor._sync_appointment_types_from_schedule()

        # Sync consultation_duration to all linked appointment types
        if 'consultation_duration' in vals:
            for doctor in self.filtered(lambda d: d.employment_type == 'doctor'):
                doctor.appointment_type_ids.filtered(lambda a: a).write({
                    'appointment_duration': doctor.consultation_duration,
                })
        return res

    # ─────────────────────────────────────────────────────────────────────
    # Core sync: appointment types from schedule
    # ─────────────────────────────────────────────────────────────────────

    def _sync_appointment_types_from_schedule(self):
        """Sync appointment.type records based on the current schedule attendances.

        Rules:
        - One appointment.type per clinic that appears in attendance_ids.
        - If a clinic is removed from the schedule, remove its appointment type.
        - Never auto-creates types just because the doctor has no slots (i.e. empty schedule = no types created).
        - Syncs appointment.slot records on existing types.
        """
        for doctor in self:
            staff_user = doctor.user_id or self.env.user
            # Collect distinct clinics that actually have schedule slots
            clinics_in_schedule = doctor.attendance_ids.mapped('clinic_id').filtered(lambda c: c.id)

            # Remove appointment types for clinics no longer in schedule
            stale = doctor.appointment_type_ids.filtered(
                lambda a: a.clinic_id and a.clinic_id not in clinics_in_schedule
            )
            if stale:
                stale.unlink()

            # Remove generic (no-clinic) appointment types leftover from old logic
            generic = doctor.appointment_type_ids.filtered(lambda a: not a.clinic_id)
            if generic:
                generic.unlink()

            # Create missing, sync existing – one per clinic in schedule
            for clinic in clinics_in_schedule:
                existing = doctor.appointment_type_ids.filtered(lambda a: a.clinic_id == clinic)[:1]
                if existing:
                    # Sync slots and duration
                    if doctor.consultation_duration:
                        existing.appointment_duration = doctor.consultation_duration
                    existing._sync_doctor_schedule()
                else:
                    appt_type = self.env['appointment.type'].create({
                        'name': _('%(doctor)s - %(clinic)s', doctor=doctor.name, clinic=clinic.name),
                        'doctor_id': doctor.id,
                        'clinic_id': clinic.id,
                        'appointment_duration': doctor.consultation_duration or 0.5,
                        'slot_creation_interval': doctor.consultation_duration or 0.5,
                        'schedule_based_on': 'users',
                        'work_hours_activated': True,
                        'category': 'recurring',
                        'staff_user_ids': [(6, 0, staff_user.ids)],
                        'max_schedule_days': 30,
                    })
                    appt_type._sync_doctor_schedule()

    # ─────────────────────────────────────────────────────────────────────
    # Action: open booked appointments
    # ─────────────────────────────────────────────────────────────────────

    def action_view_appointments(self):
        """Open the actual booked appointments (calendar.event) linked to this doctor's appointment types."""
        self.ensure_one()
        appointment_type_ids = self.appointment_type_ids.ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments'),
            'res_model': 'calendar.event',
            'view_mode': 'list,form,calendar',
            'domain': [('appointment_type_id', 'in', appointment_type_ids)],
            'context': {
                'default_appointment_type_id': appointment_type_ids[0] if appointment_type_ids else False,
            },
        }
