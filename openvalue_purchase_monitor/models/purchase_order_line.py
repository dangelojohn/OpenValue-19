# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_pending = fields.Float(
        'Qty to Receive', digits='Product Unit of Measure',
        compute='_compute_qty_pending', store=True)
    is_late = fields.Boolean('Late', compute='_compute_is_late')

    @api.depends('product_qty', 'qty_received', 'state')
    def _compute_qty_pending(self):
        for line in self:
            if line.state in ('purchase', 'done'):
                line.qty_pending = max(0.0, line.product_qty - line.qty_received)
            else:
                line.qty_pending = 0.0

    def _compute_is_late(self):
        now = fields.Datetime.now()
        for line in self:
            line.is_late = bool(
                line.qty_pending > 0 and line.date_planned and line.date_planned < now)
