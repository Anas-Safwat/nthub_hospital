from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, time, timedelta
import pytz

class HospitalTimetableSlot(models.Model):
    _name = 'hospital.timetable.slot'
    _description = 'Timetable Slot'
    _order = 'slot_date asc, hour_from asc'
    _rec_name = 'display_name'

    patient_id = fields.Many2one('hospital.patient', string="Patient")
    patient_name = fields.Char(compute='_compute_patient_name',string="Name", readonly=False)
    patient_phone = fields.Char(compute='_compute_patient_phone',string="Phone", readonly=False)
    timetable_id = fields.Many2one('hospital.timetable', ondelete='cascade')
    doctor_id = fields.Many2one('hr.employee', string="Doctor", store=True)
    slot_date = fields.Date(string="Date", required=True)
    hour_from = fields.Float(string="From")
    hour_to = fields.Float(string="To")
    type = fields.Selection([
        ('operation', 'Operation'),
        ('consultation', 'Consultation'),
    ], string="Slot Type", default='consultation')
    state = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked')
    ], default='available', string="Status")
    appointment_id = fields.Many2one('hospital.appointment', string="Appointment", readonly=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    start_datetime = fields.Datetime(string="Start Time", compute='_compute_calendar_datetimes', store=True)
    stop_datetime = fields.Datetime(string="End Time", compute='_compute_calendar_datetimes', store=True)
    duration = fields.Float(string="Duration", compute='_compute_calendar_datetimes', store=True)
    calendar_color = fields.Integer(compute='_compute_calendar_color', store=True)
    
    @api.onchange('patient_id')
    def _compute_patient_name(self):
        self.patient_name = self.patient_id.name
        
    @api.onchange('patient_id')
    def _compute_patient_phone(self):
        self.patient_phone = self.patient_id.phone
    
    
    @api.depends('state')
    def _compute_calendar_color(self):
        for slot in self:
            slot.calendar_color = 9 if slot.state == 'booked' else 10
    @api.depends('slot_date', 'hour_from', 'hour_to')
    def _compute_calendar_datetimes(self):
        # Use user's timezone so float hours align with local wall-clock time
        tz_name = self.env.user.tz or self.env.context.get('tz') or 'UTC'
        user_tz = pytz.timezone(tz_name)

        for slot in self:
            if slot.slot_date:
                fh, fm = divmod(int(round(slot.hour_from * 60)), 60)
                th, tm = divmod(int(round(slot.hour_to * 60)), 60)

                # Combine Date + Float hours into naive local datetimes
                local_start = datetime.combine(slot.slot_date, time(fh % 24, fm))
                if th >= 24:
                    local_stop = datetime.combine(slot.slot_date + timedelta(days=1), time(th % 24, tm))
                else:
                    local_stop = datetime.combine(slot.slot_date, time(th, tm))

                # Convert local time to naive UTC for Odoo Datetime storage
                slot.start_datetime = user_tz.localize(local_start).astimezone(pytz.UTC).replace(tzinfo=None)
                slot.stop_datetime = user_tz.localize(local_stop).astimezone(pytz.UTC).replace(tzinfo=None)
                slot.duration = max(0.0, slot.hour_to - slot.hour_from)
            else:
                slot.start_datetime = False
                slot.stop_datetime = False
                slot.duration = 0.0
                
    @api.depends('hour_from', 'hour_to', 'slot_date', 'doctor_id')
    def _compute_display_name(self):
        for slot in self:
            fh, fm = divmod(int(round(slot.hour_from * 60)), 60)
            th, tm = divmod(int(round(slot.hour_to * 60)), 60)
            date_str = slot.slot_date.strftime('%d/%m') if slot.slot_date else ''
            doctor_name = slot.doctor_id.name or ''
            slot.display_name = f"{date_str} {fh:02d}:{fm:02d}-{th:02d}:{tm:02d} ({doctor_name})"

    def action_book_appointment(self):
        """Create a draft appointment from this slot and close the popup."""
        self.ensure_one()
        if self.state == 'booked':
            raise UserError(_("This slot is already booked."))

        appointment = self.env['hospital.appointment'].create({
            'patient_id': self.patient_id.id if self.patient_id else False,
            'patient_name': self.patient_name or '',
            'patient_phone': self.patient_phone or '',
            'doctor_id': self.doctor_id.id,
            'appointment_date': self.slot_date,
            'slot_id': self.id,
            'timetable_id': self.timetable_id.id,
            'state': 'draft',
        })
        self.write({
            'state': 'booked',
            'appointment_id': appointment.id,
        })
        return {'type': 'ir.actions.act_window_close'}