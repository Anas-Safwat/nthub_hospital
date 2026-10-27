from odoo import models
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_payment_state(self):
        res = super()._compute_payment_state()
        paid_moves = self.filtered(
            lambda m: m.payment_state in ('paid', 'in_payment')
        )
        if paid_moves:
            paid_moves._dispense_visit_medicines()
        return res

    def _dispense_visit_medicines(self):
        """Auto-create delivery orders for visits whose invoice
        has just been paid."""
        visits = self.env['hospital.visit'].search([
            ('invoice_id', 'in', self.ids),
            ('picking_id', '=', False),
            ('state', '=', 'done'),
        ])
        for visit in visits:
            if visit.medicine_line_ids:
                visit._create_medicine_picking()
                _logger.info(
                    'Invoice %s paid — dispensed medicines for visit %s',
                    visit.invoice_id.name, visit.id,
                )