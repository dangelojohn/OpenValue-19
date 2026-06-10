# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    stock_onhand_value = fields.Float(
        'On-hand Value', compute='_compute_stock_onhand_value',
        digits='Product Price',
        help="On-hand quantity valued at the product cost.")

    @api.depends('qty_available', 'standard_price')
    def _compute_stock_onhand_value(self):
        for product in self:
            product.stock_onhand_value = product.qty_available * product.standard_price
