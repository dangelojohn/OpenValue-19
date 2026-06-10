# -*- coding: utf-8 -*-

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _sfc_compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        """Standard unit cost rolled up from a BoM using this module's costing
        rates (variable + fixed operation rates, components, by-products,
        subcontracting).

        NOTE (Odoo 19): the legacy core hook ``_compute_bom_price`` that this
        used to override no longer exists on ``product.product`` in v19 — BoM
        cost is surfaced through the BoM Structure report instead (see
        ``mrp.routing.workcenter._compute_cost``).  This method preserves the
        full proprietary rollup so it can be called from a cost-update flow;
        wire it to the desired trigger once confirmed on the v19 instance.
        """
        self.ensure_one()
        if not bom or byproduct_bom:
            return 0.0
        if not boms_to_recompute:
            boms_to_recompute = []
        bom_qty = bom.product_qty or 1.0
        total = costvar = costfixed = byproductamount = price = 0.0
        # operations
        for operation in bom.operation_ids:
            if operation._skip_operation_line(self):
                continue
            workcenter = operation.workcenter_id
            if not workcenter:
                continue
            efficiency = workcenter.time_efficiency or 100.0
            costvar += (operation.time_cycle * 100.0 / efficiency) * workcenter.costs_hour / 60.0
            costfixed += ((workcenter.time_stop + workcenter.time_start) * workcenter.costs_hour_fixed / 60.0) * bom_qty
        total += costvar + costfixed
        # components
        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._sfc_compute_bom_price(
                    line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(
                    line.product_id.standard_price, line.product_uom_id) * line.product_qty
        # by-products
        for byproduct in bom.byproduct_ids:
            byproductamount += byproduct.product_id.standard_price * byproduct.product_qty
        total -= byproductamount
        # subcontracting (only reachable with mrp_subcontracting installed)
        if bom.type == "subcontract":
            product = bom.product_id or bom.product_tmpl_id.product_variant_ids[:1]
            suppliers = product._prepare_sellers()
            if suppliers and suppliers[0].partner_id in bom.subcontractor_ids:
                price = suppliers[0].price / bom_qty
        total += price
        return bom.product_uom_id._compute_price(total / bom_qty, self.uom_id)
