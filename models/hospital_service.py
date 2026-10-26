from odoo import models, fields


class HospitalService(models.Model):
    _name = 'hospital.service'
    _description = 'Hospital Service'
    _order = 'sequence, name'

    name = fields.Char(string='Service Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one(
        'product.product', string='Service Product',
        required=True, domain="[('type', '=', 'service')]",
        help="The billable service product linked to this hospital service.",
    )
    price = fields.Float(
        string='Price', related='product_id.lst_price',
        readonly=False,
        help="Standard price managed by the hospital. "
             "Changing this updates the product's sale price.",
    )
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
