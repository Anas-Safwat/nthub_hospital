from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HospitalTimetableSlot(models.Model):
    _name = 'hospital.timetable.slot'
    _description = 'Timetable Slot'
    _order = 'slot_date asc, hour_from asc'
    _rec_name = 'display_name'

    timetable_id = fields.Many2one('hospital.timetable', ondelete='cascade')
    doctor_id = fields.Many2one('hr.employee', string="Doctor", store=True)
    slot_date = fields.Date(string="Date", required=True)
    hour_from = fields.Float(string="From")
    hour_to = fields.Float(string="To")
    state = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked')
    ], default='available', string="Status")

    appointment_id = fields.Many2one('hospital.appointment', string="Appointment", readonly=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('hour_from', 'hour_to', 'slot_date', 'doctor_id')
    def _compute_display_name(self):
        for slot in self:
            fh, fm = divmod(int(round(slot.hour_from * 60)), 60)
            th, tm = divmod(int(round(slot.hour_to * 60)), 60)
            date_str = slot.slot_date.strftime('%d/%m') if slot.slot_date else ''
            doctor_name = slot.doctor_id.name or ''
            slot.display_name = f"{date_str} {fh:02d}:{fm:02d}-{th:02d}:{tm:02d} ({doctor_name})"

    def action_book_appointment(self):
        """Open a pre-filled appointment form to book this slot."""
        self.ensure_one()
        if self.state == 'booked':
            raise UserError(_("This slot is already booked."))
        return {
            'name': _('Book Appointment'),
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.appointment',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_doctor_id': self.doctor_id.id,
                'default_appointment_date': str(self.slot_date),
                'default_slot_id': self.id,
                'default_timetable_id': self.timetable_id.id,
            },
        }