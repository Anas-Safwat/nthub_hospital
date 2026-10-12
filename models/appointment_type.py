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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.doctor_id and record.doctor_id.user_id:
                # Auto-assign the doctor's user as the staff user
                record.staff_user_ids = record.doctor_id.user_id
        return records

    def _sync_doctor_schedule(self):
        """Sync appointment slots with the doctor's resource calendar attendances.

        Reads the doctor's working hours (resource.calendar.attendance lines)
        filtered by the specific clinic (if set), and creates matching
        appointment.slot records so that _slots_generate() produces the right
        time windows for each clinic.
        """
        for record in self:
            if not record.doctor_id:
                continue

            calendar = record.doctor_id.resource_calendar_id
            if not calendar:
                continue

            # Remove old recurring slots (keep any manually-created unique slots)
            record.slot_ids.filtered(lambda s: s.slot_type == 'recurring').unlink()

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
