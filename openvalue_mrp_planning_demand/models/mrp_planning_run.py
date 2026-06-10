# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import fields, models


class MrpPlanningRun(models.Model):
    _inherit = 'mrp.planning.run'

    include_sales_demand = fields.Boolean(
        'Include Sales Demand', default=True,
        help="Add planned supply to cover open sales-order demand.")

    def action_run(self):
        res = super().action_run()
        if self.include_sales_demand:
            self._add_sales_demand_lines()
            if hasattr(type(self), '_explode_dependent_demand'):
                self._explode_dependent_demand()
        return res

    def _supply_qty(self, product):
        scoped = product.with_context(warehouse=self.warehouse_id.id)
        return scoped.qty_available + scoped.incoming_qty

    def _add_sales_demand_lines(self):
        self.ensure_one()
        Line = self.env['mrp.planning.line']
        Bom = self.env['mrp.bom']
        sol = self.env['sale.order.line'].search([
            ('order_id.state', '=', 'sale'),
            ('product_id.is_storable', '=', True),
            ('display_type', '=', False),
            ('company_id', '=', self.company_id.id),
        ])
        demand = defaultdict(float)
        for line in sol:
            remaining = line.product_uom_qty - line.qty_delivered
            if remaining > 0:
                demand[line.product_id] += remaining
        for product, gross in demand.items():
            already = sum(self.line_ids.filtered(
                lambda l: l.product_id == product).mapped('suggested_qty'))
            net = gross - self._supply_qty(product) - already
            if net <= 0:
                continue
            bom = Bom._bom_find(product)[product]
            Line.create({
                'run_id': self.id,
                'product_id': product.id,
                'forecast_qty': self._supply_qty(product),
                'suggested_qty': net,
                'supply_type': 'manufacture' if bom else 'buy',
                'planned_date': self.date,
            })
        return True
