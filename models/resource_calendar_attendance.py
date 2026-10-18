from odoo import models, fields, api, _


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    clinic_id = fields.Many2one(comodel_name='hospital.clinic', string='Clinic')

    # ── Req #2: Computed name field ───────────────────────────────────────
    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        readonly=False,   # allow manual override if ever needed
        required=False,   # override base required=True; value is always set by _compute_name
        help='Auto-computed as "Day HH:MM-HH:MM [Clinic]". You may override it manually.',
    )

    @api.depends('dayofweek', 'hour_from', 'hour_to', 'clinic_id')
    def _compute_name(self):
        day_labels = {
            '0': _('Monday'),
            '1': _('Tuesday'),
            '2': _('Wednesday'),
            '3': _('Thursday'),
            '4': _('Friday'),
            '5': _('Saturday'),
            '6': _('Sunday'),
        }
        for rec in self:
            day = day_labels.get(rec.dayofweek, rec.dayofweek or '')
            h_from = rec.hour_from or 0.0
            h_to = rec.hour_to or 0.0
            from_str = '%02d:%02d' % (int(h_from), round((h_from % 1) * 60))
            to_str = '%02d:%02d' % (int(h_to), round((h_to % 1) * 60))
            if rec.clinic_id:
                rec.name = '%s %s-%s (%s)' % (day, from_str, to_str, rec.clinic_id.name)
            else:
                rec.name = '%s %s-%s' % (day, from_str, to_str)

    # ── Helper: find doctors and trigger sync ─────────────────────────────
    def _get_linked_doctors(self):
        """Return hr.employee (doctors) that use the calendars of these attendance records."""
        calendar_ids = self.mapped('calendar_id').ids
        if not calendar_ids:
            return self.env['hr.employee']
        return self.env['hr.employee'].search([
            ('resource_calendar_id', 'in', calendar_ids),
            ('employment_type', '=', 'doctor'),
        ])

    def _trigger_doctor_sync(self):
        """Trigger appointment type sync for all doctors affected by these attendance changes."""
        doctors = self._get_linked_doctors()
        if doctors:
            doctors._sync_appointment_types_from_schedule()

    # ── Req #3 + #6: Sync on create/write ────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Sync appointment types for affected doctors when new schedule rows are added.
        # Guard: skip if we're already in a sync cascade (e.g. called from _sync_doctor_schedule)
        if not self.env.context.get('skip_attendance_sync'):
            records._trigger_doctor_sync()
        return records

    def write(self, vals):
        res = super().write(vals)
        # Sync when clinic or timing changes (affects appointment type syncing)
        if not self.env.context.get('skip_attendance_sync'):
            if any(k in vals for k in ('clinic_id', 'dayofweek', 'hour_from', 'hour_to')):
                self._trigger_doctor_sync()
        return res

    # ── Req #3: Sync slot deletion – attendance → appointment.slot ────────
    def unlink(self):
        """When an attendance row is deleted, also delete the matching appointment.slot(s)
        in any appointment.type linked to the same doctor's resource calendar."""
        # Collect matching appointment.slots before deletion
        slots_to_unlink = self.env['appointment.slot']
        for att in self:
            calendar = att.calendar_id
            if not calendar:
                continue
            # dayofweek in attendance is 0=Mon, weekday in slot is '1'=Mon
            slot_weekday = str(int(att.dayofweek) + 1)
            # Find appointment types linked to doctors using this calendar
            doctors = self.env['hr.employee'].search([
                ('resource_calendar_id', '=', calendar.id),
                ('employment_type', '=', 'doctor'),
            ])
            appt_types = self.env['appointment.type'].search([
                ('doctor_id', 'in', doctors.ids),
            ])
            matching_slots = appt_types.mapped('slot_ids').filtered(
                lambda s: (
                    s.slot_type == 'recurring'
                    and s.weekday == slot_weekday
                    and abs(s.start_hour - att.hour_from) < 0.01
                    and abs(s.end_hour - att.hour_to) < 0.01
                )
            )
            slots_to_unlink |= matching_slots

        res = super().unlink()
        if slots_to_unlink:
            # Use sudo to avoid permission issues and prevent recursive deletion loops
            slots_to_unlink.with_context(skip_attendance_sync=True).unlink()
        return res