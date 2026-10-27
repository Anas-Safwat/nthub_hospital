from odoo import models, _

import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        res = super().write(vals)
        if 'payment_state' in vals and vals['payment_state'] in ('paid', 'in_payment'):
            self._dispense_visit_medicines()
        return res

    def _dispense_visit_medicines(self):
        """Auto-create delivery orders for visits whose invoice
        has just been paid."""
        visits = self.env['hospital.visit'].search([
            ('invoice_id', 'in', self.ids),
            ('picking_id', '=', False),
        ])
        for visit in visits:
            if visit.medicine_line_ids:
                visit._create_medicine_picking()
                _logger.info(
                    'Invoice %s paid — dispensed medicines for visit %s',
                    visit.invoice_id.name, visit.id,
                )
