# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    type_id = fields.Many2one(
        'purchase.order.type', 'Order Type',
        help="Classification of this purchase order.")
