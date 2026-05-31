# -*- coding: utf-8 -*-

from odoo import api, models


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    @api.depends('time_total', 'workcenter_id',
                 'workcenter_id.costs_hour', 'workcenter_id.costs_hour_fixed')
    def _compute_cost(self):
        """Re-home the legacy ``product._compute_bom_price`` operation costing.

        In Odoo 19 the product-level ``_compute_bom_price`` hook no longer
        exists; BoM cost is surfaced through the BoM Structure report, which
        reads ``mrp.routing.workcenter.cost``.  We extend that compute so the
        operation cost includes both the variable rate (efficiency-adjusted via
        ``time_total``) and the fixed setup/cleanup rate.
        """
        super()._compute_cost()
        for operation in self:
            workcenter = operation.workcenter_id
            if not workcenter:
                continue
            fixed = ((workcenter.time_start + workcenter.time_stop) / 60.0) * workcenter.costs_hour_fixed
            operation.cost += fixed
