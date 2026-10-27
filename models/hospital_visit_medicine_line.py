from odoo import models, fields, api


class HospitalVisitMedicineLine(models.Model):
    _name = 'hospital.visit.medicine.line'
    _description = 'Visit Medicine / Prescription Line'

    visit_id = fields.Many2one(
        'hospital.visit', string='Visit',
        required=True, ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product', string='Medicine',
        required=True,
        domain="[('is_storable', '=', True)]",
    )
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price')
    subtotal = fields.Float(
        string='Subtotal', compute='_compute_subtotal', store=True,
    )
    invoice_line_id = fields.Many2one(
        'account.move.line', string='Invoice Line',
        readonly=True, copy=False,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ── Clinical / prescription fields ────────────────────────────
    dosage = fields.Char(string='Dosage', help='e.g., "500mg"')
    frequency = fields.Char(string='Frequency', help='e.g., "3 times/day"')
    duration = fields.Char(string='Duration', help='e.g., "7 days"')
    instructions = fields.Text(string='Instructions')

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
