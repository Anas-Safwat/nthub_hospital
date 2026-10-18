import pytz

from odoo import models, fields, api, _


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    doctor_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Doctor',
        domain=[('employment_type', '=', 'doctor')],
        help='Doctor linked to this appointment type.',
    )
    doctor_clinic_ids = fields.Many2many(
        related='doctor_id.clinic_ids',
        string="Doctor's Clinics",
    )
    clinic_id = fields.Many2one(
        comodel_name='hospital.clinic',
        string='Clinic',
        domain="[('id', 'in', doctor_clinic_ids)]",
        help='Clinic location for this appointment type.',
    )

    @api.constrains('category', 'start_datetime', 'end_datetime')
    def _check_appointment_category_time_boundaries(self):
        """Override: Doctor-managed appointment types are always 'recurring' but may have optional
        validity start/end dates (used in the Clinics Validity page). Skip the punctual check for them."""
        # Only enforce the built-in constraint for non-doctor-managed types
        non_doctor_types = self.filtered(lambda a: not a.doctor_id)
        super(AppointmentType, non_doctor_types)._check_appointment_category_time_boundaries()

    @api.depends('start_datetime', 'end_datetime')
    def _compute_category(self):
        """Override: Doctor-managed types stay 'recurring' regardless of start/end datetime.
        For all other types, use the standard Odoo behavior."""
        doctor_types = self.filtered(lambda a: a.doctor_id)
        # Doctor-managed: always recurring (they use start/end datetime for info only)
        for rec in doctor_types:
            if not rec.category:
                rec.category = 'recurring'
        # Non-doctor: standard behavior
        super(AppointmentType, self - doctor_types)._compute_category()

    def _slots_generate(self, first_day, last_day, timezone, reference_date=None):
        """Override: clamp the slot generation window to the validity period
        (start_datetime / end_datetime) for doctor-managed recurring appointment types.

        Standard Odoo ignores start/end_datetime for 'recurring' types and uses
        ``reference_date + max_schedule_days`` instead.  For doctor-managed types
        we set category='recurring' but still use start/end_datetime as a validity
        window, so we must enforce that boundary ourselves.

        By clamping `first_day` and `last_day` here we ensure that no slots are
        generated outside the doctor's configured availability period for this clinic.
        """
        if self.doctor_id and self.category == 'recurring':
            # Clamp to validity start (start_datetime)
            if self.start_datetime:
                validity_start_utc = self.start_datetime.replace(tzinfo=pytz.UTC)
                if validity_start_utc > first_day:
                    first_day = validity_start_utc

            # Clamp to validity end (end_datetime)
            if self.end_datetime:
                validity_end_utc = self.end_datetime.replace(tzinfo=pytz.UTC)
                if validity_end_utc < last_day:
                    last_day = validity_end_utc

            # If the validity window has already passed, no slots
            if first_day >= last_day:
                return []

        return super()._slots_generate(first_day, last_day, timezone, reference_date=reference_date)

    def _sync_doctor_schedule(self):
        """Sync appointment slots and staff user with the doctor's resource calendar attendances.

        Reads the doctor's working hours (resource.calendar.attendance lines)
        filtered by the specific clinic (if set), and creates matching
        appointment.slot records so that _slots_generate() produces the right
        time windows for each clinic.

        Also ensures staff_user_ids always reflects the doctor's own linked user.
        """
        for record in self:
            if not record.doctor_id:
                continue

            # --- Always ensure the doctor's own user is the staff user ---
            doctor_user = record.doctor_id.user_id
            if doctor_user and record.staff_user_ids != doctor_user:
                record.staff_user_ids = [(6, 0, doctor_user.ids)]

            calendar = record.doctor_id.resource_calendar_id
            if not calendar:
                continue

            # Remove old recurring slots (keep any manually-created unique slots)
            # Use context flag to avoid triggering reverse sync on unlink
            record.slot_ids.filtered(
                lambda s: s.slot_type == 'recurring'
            ).with_context(skip_attendance_sync=True).unlink()

            # Filter attendances: only shifts for this clinic (or all if no clinic set)
            attendances = calendar.attendance_ids.filtered(
                lambda a: a._is_work_period() and (not record.clinic_id or a.clinic_id == record.clinic_id)
            )

            slot_vals = []
            for att in attendances:
                slot_vals.append({
                    'appointment_type_id': record.id,
                    'weekday': str(int(att.dayofweek) + 1),  # attendance: '0'=Mon, slot: '1'=Mon
                    'start_hour': att.hour_from,
                    'end_hour': att.hour_to if att.hour_to else 0.0,  # 0 = midnight (next day)
                })

            if slot_vals:
                self.env['appointment.slot'].create(slot_vals)


class AppointmentSlot(models.Model):
    _inherit = 'appointment.slot'

    def unlink(self):
        """Req #3: When a slot is deleted from the Availability page of appointment.type,
        also delete the matching resource.calendar.attendance row from the doctor's schedule.

        Uses context flag 'skip_attendance_sync' to avoid recursive deletion loops.
        """
        # Guard: skip reverse sync if we're already in a sync cascade
        if self.env.context.get('skip_attendance_sync'):
            return super().unlink()

        attendances_to_unlink = self.env['resource.calendar.attendance']
        for slot in self:
            appt_type = slot.appointment_type_id
            if not appt_type or not appt_type.doctor_id or slot.slot_type != 'recurring':
                continue
            calendar = appt_type.doctor_id.resource_calendar_id
            if not calendar:
                continue
            # weekday in slot: '1'=Mon; dayofweek in attendance: '0'=Mon
            att_dayofweek = str(int(slot.weekday) - 1)
            matching_att = calendar.attendance_ids.filtered(
                lambda a: (
                    a.dayofweek == att_dayofweek
                    and abs(a.hour_from - slot.start_hour) < 0.01
                    and abs(a.hour_to - slot.end_hour) < 0.01
                    and (not appt_type.clinic_id or a.clinic_id == appt_type.clinic_id)
                )
            )
            attendances_to_unlink |= matching_att

        res = super().unlink()
        if attendances_to_unlink:
            # Use sudo and context flag to prevent recursive loop back into AppointmentSlot.unlink
            attendances_to_unlink.sudo().with_context(skip_attendance_sync=True).unlink()
        return res
