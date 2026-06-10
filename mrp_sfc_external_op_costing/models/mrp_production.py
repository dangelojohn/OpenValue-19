# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    external_direct_cost = fields.Float(
        'External Direct Cost', digits='Product Price',
        compute='_compute_external_direct_cost', store=True,
        help="Confirmed outsourced-operation purchase cost for this order.")

    @api.depends('external_po_line_ids.price_subtotal',
                 'external_po_line_ids.order_id.state')
    def _compute_external_direct_cost(self):
        for production in self:
            lines = production.external_po_line_ids.filtered(
                lambda l: l.order_id.state in ('purchase', 'done'))
            production.external_direct_cost = sum(lines.mapped('price_subtotal'))

    def button_closure(self):
        res = super().button_closure()
        for record in self:
            extra = record.external_direct_cost
            if extra:
                # The base closure already set industrial_cost from in-house
                # direct + overhead costs; add the outsourced purchase cost.
                qty = record._get_qty_produced()
                record.industrial_cost += extra
                record.industrial_cost_unit = (
                    record.industrial_cost / qty if qty else 0.0)
        return res
