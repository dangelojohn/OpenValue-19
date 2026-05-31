# -*- coding: utf-8 -*-


from odoo import api, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        self.ensure_one()
        if not bom:
            return 0
        # esclusione delle by-product boms
        if byproduct_bom:
            return 0
        # guard the final per-unit division (total / bom.product_qty).
        if not bom.product_qty:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        #total = 0
        total = costvar = costfixed = byproductamount = price = 0.0
        # operations
        for operation in bom.operation_ids:
            if operation._skip_operation_line(self):
                continue
            #costvar += (operation.time_cycle/60) * operation.workcenter_id.costs_hour
            #costfixed += (operation.workcenter_id.time_stop + operation.workcenter_id.time_start) * operation.workcenter_id.costs_hour_fixed/60
            # skip operations whose workcenter would divide by zero.
            if not operation.workcenter_id.time_efficiency:
                continue
            costvar += (operation.time_cycle * 100.0 / operation.workcenter_id.time_efficiency) * operation.workcenter_id.costs_hour / 60
            # NOTE [design decision - confirm intent]: costfixed is multiplied by
            # bom.product_qty here, then the grand total is divided by bom.product_qty
            # at the return, so setup/teardown (fixed) cost is charged in FULL per
            # unit rather than amortised across the batch. Preserved as-is from v16.
            costfixed += ((operation.workcenter_id.time_stop + operation.workcenter_id.time_start) * operation.workcenter_id.costs_hour_fixed / 60) * bom.product_qty
        total += costvar + costfixed
        # components
        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue
            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty
        # by products
        for byproduct_id in bom.byproduct_ids:
            byproductamount += byproduct_id.product_id.standard_price * byproduct_id.product_qty
        total -= byproductamount
        # subcontracting
        if bom.type == "subcontract":
            product = bom.product_id or bom.product_tmpl_id.product_variant_ids[0]
            suppliers = product._prepare_sellers()
            if suppliers:
                if suppliers[0].name in bom.subcontractor_ids:
                    price = suppliers[0].price / bom.product_qty
        total += price
        return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)
