from odoo import models, fields, api, _
from datetime import timedelta


class HospitalTimetable(models.Model):
    _name = 'hospital.timetable'
    _description = 'Doctor Timetable'
    _order = 'date_from desc'

    name = fields.Char(string="Title",compute='_compute_name',store=True,readonly=False)
    doctor_id = fields.Many2one('hr.employee', string="Doctor", required=True,
                                domain="[('employment_type', '=', 'doctor')]")
    slot_duration = fields.Float(string="Slot Duration (Minutes)", default=30.0)
    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)
    slot_ids = fields.One2many('hospital.timetable.slot', 'timetable_id', string="Generated Slots")
 
    # ── Computed slot counts ─────────────────────────────────────────
    slot_count = fields.Integer(compute='_compute_slot_counts', string="Total Slots", store=True)
    available_slot_count = fields.Integer(compute='_compute_slot_counts', string="Available Slots", store=True)
    booked_slot_count = fields.Integer(compute='_compute_slot_counts', string="Booked Slots", store=True)

    @api.depends('slot_ids', 'slot_ids.state')
    def _compute_slot_counts(self):
        for rec in self:
            rec.slot_count = len(rec.slot_ids)
            rec.available_slot_count = len(rec.slot_ids.filtered(lambda s: s.state == 'available'))
            rec.booked_slot_count = len(rec.slot_ids.filtered(lambda s: s.state == 'booked'))

    def action_generate_slots(self):
        for rec in self:
            # Only remove available (un-booked) slots — keep booked ones intact
            rec.slot_ids.filtered(lambda s: s.state == 'available').unlink()

            current_date = rec.date_from
            duration_hours = (rec.slot_duration or 30.0) / 60.0
            slots_to_create = []

            attendances = rec.doctor_id.resource_calendar_id.attendance_ids

            while current_date <= rec.date_to:
                day_str = str(current_date.weekday())

                day_lines = attendances.filtered(
                    lambda a: a.dayofweek == day_str and a.day_period != 'lunch'
                )

                for line in day_lines:
                    current_hour = line.hour_from
                    while round(current_hour + duration_hours, 4) <= line.hour_to:
                        slots_to_create.append({
                            'timetable_id': rec.id,
                            'doctor_id': rec.doctor_id.id,
                            'slot_date': current_date,
                            'hour_from': current_hour,
                            'hour_to': current_hour + duration_hours,
                            'type': line.type,
                            'state': 'available',
                        })
                        current_hour += duration_hours

                current_date += timedelta(days=1)

            self.env['hospital.timetable.slot'].create(slots_to_create)
            

    @api.depends('doctor_id', 'date_from', 'date_to')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.doctor_id:
                parts.append('Dr '+rec.doctor_id.name)

            if rec.date_from and rec.date_to:
                # If both dates are in the same month & year -> "January 2026"
                if (rec.date_from.month == rec.date_to.month
                        and rec.date_from.year == rec.date_to.year):
                    parts.append(rec.date_from.strftime('%B %Y'))
                else:
                    parts.append(
                        f"{rec.date_from.strftime('%d/%m/%Y')} - {rec.date_to.strftime('%d/%m/%Y')}"
                    )
            elif rec.date_from:
                parts.append(rec.date_from.strftime('%d/%m/%Y'))

            rec.name = " – ".join(parts) if parts else _("New Timetable")