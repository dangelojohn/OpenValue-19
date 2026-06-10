# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import fields, models


class MrpPlanningRun(models.Model):
    _inherit = 'mrp.planning.run'

    multilevel = fields.Boolean(
        'Multi-level', default=True,
        help="Explode dependent component demand through the BoM after the "
             "reorder-point run.")

    def action_run(self):
        res = super().action_run()
        if self.multilevel:
            self._explode_dependent_demand()
        return res

    def _explode_dependent_demand(self):
        """Cascade dependent demand: for each proposed manufacturing line,
        explode its BoM, net the component requirements against availability,
        and propose component supply - recursively down the structure."""
        self.ensure_one()
        Bom = self.env['mrp.bom']
        Line = self.env['mrp.planning.line']
        processed = set()
        guard = 0
        while guard < 50:
            guard += 1
            pending = self.line_ids.filtered(
                lambda l: l.supply_type == 'manufacture'
                and l.suggested_qty and l.id not in processed)
            if not pending:
                break
            for line in pending:
                processed.add(line.id)
                bom = Bom._bom_find(line.product_id)[line.product_id]
                if not bom:
                    continue
                _boms, blines = bom.explode(line.product_id, line.suggested_qty)
                demand = defaultdict(float)
                for bom_line, data in blines:
                    demand[bom_line.product_id] += data['qty']
                for product, gross in demand.items():
                    forecast = product.with_context(
                        warehouse=self.warehouse_id.id).virtual_available
                    already = sum(self.line_ids.filtered(
                        lambda l: l.product_id == product).mapped('suggested_qty'))
                    net = gross - max(0.0, forecast) - already
                    if net <= 0:
                        continue
                    child_bom = Bom._bom_find(product)[product]
                    Line.create({
                        'run_id': self.id,
                        'product_id': product.id,
                        'forecast_qty': forecast,
                        'suggested_qty': net,
                        'supply_type': 'manufacture' if child_bom else 'buy',
                        'planned_date': self.date,
                    })
        return True
