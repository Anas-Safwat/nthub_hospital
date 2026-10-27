from odoo import models, fields, api


class HospitalVisitServiceLine(models.Model):
    _name = 'hospital.visit.service.line'
    _description = 'Visit Service Line'

    visit_id = fields.Many2one(
        'hospital.visit', string='Visit',
        required=True, ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product', string='Service',
        required=True, domain="[('type', '=', 'service')]",
    )
    name = fields.Char(string='Description')
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

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
