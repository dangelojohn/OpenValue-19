# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    production_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order', index=True, copy=False)
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order', index=True, copy=False)
