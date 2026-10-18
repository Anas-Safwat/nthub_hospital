from odoo import models, fields, api, _


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    clinic_id = fields.Many2one(comodel_name='hospital.clinic', string='Clinic')
    type = fields.Selection([('operation','Operation'),('consultation','Consultation')])
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

  