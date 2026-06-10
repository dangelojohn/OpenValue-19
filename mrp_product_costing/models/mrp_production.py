# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # standard unit costs
    std_prod_cost = fields.Float('Current Standard Cost', digits='Product Price', compute='_compute_standard_costs', store=True, aggregator="avg")
    std_mat_cost = fields.Float('Standard Material Unit Cost', digits='Product Price', compute='_compute_standard_costs', store=True, aggregator="avg")
    std_var_cost = fields.Float('Standard Direct Variable Unit Cost', digits='Product Price', compute='_compute_standard_costs', store=True, aggregator="avg")
    std_fixed_cost = fields.Float('Standard Direct Fixed Unit Cost', digits='Product Price', compute='_compute_standard_costs', store=True, aggregator="avg")
    std_direct_cost = fields.Float('Standard Direct Unit Cost', digits='Product Price', compute='_compute_standard_costs', store=True, aggregator="avg")
    std_byproduct_amount = fields.Float('Standard ByProduct Amount', digits='Product Price', compute='_compute_standard_costs', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)

    # planned costs (snapshot taken at confirmation / backorder split)
    planned_mat_cost = fields.Float('Planned Material Cost', digits='Product Price', readonly=True, copy=False)
    planned_mat_cost_unit = fields.Float('Planned Material Unit Cost', digits='Product Price', readonly=True, copy=False, aggregator="avg")
    planned_var_cost = fields.Float('Planned Direct Variable Cost', digits='Product Price', readonly=True, copy=False)
    planned_var_cost_unit = fields.Float('Planned Direct Variable Unit Cost', digits='Product Price', readonly=True, copy=False, aggregator="avg")
    planned_fixed_cost = fields.Float('Planned Direct Fixed Cost', digits='Product Price', readonly=True, copy=False)
    planned_fixed_cost_unit = fields.Float('Planned Direct Fixed Unit Cost', digits='Product Price', readonly=True, copy=False, aggregator="avg")
    planned_direct_cost = fields.Float('Planned Direct Cost', digits='Product Price', readonly=True, copy=False)
    planned_direct_cost_unit = fields.Float('Planned Direct Unit Cost', digits='Product Price', readonly=True, copy=False, aggregator="avg")
    planned_byproduct_amount = fields.Float('Planned ByProduct Amount', digits='Product Price', readonly=True, copy=False)
    planned_byproduct_amount_unit = fields.Float('Planned ByProduct Unit Amount', digits='Product Price', readonly=True, copy=False, aggregator="avg")

    # actual costs
    mat_cost = fields.Float('Actual Components Cost', digits='Product Price', compute='_compute_actual_material_cost', store=True)
    mat_cost_unit = fields.Float('Actual Components Unit Cost', digits='Product Price', compute='_compute_actual_material_cost', store=True, aggregator="avg")
    var_cost = fields.Float('Actual Direct Variable Cost', digits='Product Price', compute='_compute_actual_costs', store=True)
    var_cost_unit = fields.Float('Actual Direct Variable Unit Cost', digits='Product Price', compute='_compute_actual_costs', store=True, aggregator="avg")
    fixed_cost = fields.Float('Actual Direct Fixed Cost', digits='Product Price', compute='_compute_actual_costs', store=True)
    fixed_cost_unit = fields.Float('Actual Direct Fixed Unit Cost', digits='Product Price', compute='_compute_actual_costs', store=True, aggregator="avg")
    direct_cost = fields.Float('Actual Full Direct Cost', digits='Product Price', compute='_compute_actual_costs', store=True)
    direct_cost_unit = fields.Float('Actual Full Direct Unit Cost', digits='Product Price', compute='_compute_actual_costs', store=True, aggregator="avg")
    by_product_amount = fields.Float('Actual ByProduct Amount', digits='Product Price', compute='_compute_actual_by_product_amount', store=True)
    by_product_amount_unit = fields.Float('Actual ByProduct Unit Amount', digits='Product Price', compute='_compute_actual_by_product_amount', store=True, aggregator="avg")

    # delta costs = actual - planned
    delta_mat_cost = fields.Float('Delta Components Cost', digits='Product Price', compute='_compute_delta_costs', store=True)
    delta_var_cost = fields.Float('Delta Direct Variable Cost', digits='Product Price', compute='_compute_delta_costs', store=True)
    delta_fixed_cost = fields.Float('Delta Direct Fixed Cost', digits='Product Price', compute='_compute_delta_costs', store=True)
    delta_direct_cost = fields.Float('Delta Direct Cost', digits='Product Price', compute='_compute_delta_costs', store=True)
    delta_byproduct = fields.Float('Delta ByProduct Amount', digits='Product Price', compute='_compute_delta_costs', store=True)

    wip_amount = fields.Float('WIP Amount', digits='Product Price', compute='_compute_wip_amount', store=True)

    def _get_qty_produced(self):
        self.ensure_one()
        qty_produced = 1.0
        if self.product_id and self.product_qty:
            if self.qty_producing:
                qty_produced = self.product_uom_id._compute_quantity(
                    self.qty_producing, self.product_id.product_tmpl_id.uom_id)
            else:
                qty_produced = self.product_uom_qty
        return qty_produced or 1.0

    # --- standard costs -------------------------------------------------------
    @api.depends('bom_id', 'bom_id.operation_ids', 'bom_id.bom_line_ids',
                 'bom_id.byproduct_ids', 'product_qty', 'product_uom_qty')
    def _compute_standard_costs(self):
        for production in self:
            costmat = costvar = costfixed = byproductamount = 0.0
            bom = production.bom_id
            qty = production.product_uom_qty or 1.0
            bom_qty = bom.product_qty or 1.0 if bom else 1.0
            if bom:
                dummy, lines = bom.explode(production.product_id, 1)
                for sbom, sbom_data in lines:
                    costmat += sbom.product_id.standard_price * sbom_data['qty'] / bom_qty
                for operation in bom.operation_ids:
                    workcenter = operation.workcenter_id
                    if not workcenter:
                        continue
                    capacity = workcenter._sfc_capacity(production.product_id) or 1.0
                    efficiency = workcenter.time_efficiency or 100.0
                    cycle_number = float_round(qty / capacity, precision_digits=0, rounding_method='UP')
                    costvar += (((cycle_number * operation.time_cycle * 100.0 / efficiency) / 60.0)
                                * workcenter.costs_hour) / qty / bom_qty
                    costfixed += ((workcenter.time_stop + workcenter.time_start)
                                  * workcenter.costs_hour_fixed / 60.0) / qty
                for byproduct in bom.byproduct_ids:
                    byproductamount += byproduct.product_id.standard_price * byproduct.product_qty / bom_qty
            production.std_prod_cost = production.product_id.standard_price
            production.std_byproduct_amount = byproductamount
            production.std_mat_cost = costmat
            production.std_var_cost = costvar
            production.std_fixed_cost = costfixed
            production.std_direct_cost = costvar + costfixed + costmat - byproductamount

    # --- planned costs (snapshot) --------------------------------------------
    def _apply_planned_costs(self):
        """Snapshot planned costs from current BoM/work-order data.  Called at
        confirmation and on backorder split — planned costs are a frozen
        baseline, not a live compute."""
        for production in self:
            plannedmat = plannedvar = plannedfixed = plannedreceipt = 0.0
            qty = production.product_uom_qty or 1.0
            for move in production.move_raw_ids.filtered(lambda r: r.state != 'cancel'):
                plannedmat += move.product_id.standard_price * move.product_qty
            for workorder in production.workorder_ids:
                workcenter = workorder.workcenter_id
                efficiency = (workcenter.time_efficiency or 100.0) if workcenter else 100.0
                working = (workorder.duration_expected
                           - (workcenter.time_start if workcenter else 0.0)
                           - (workcenter.time_stop if workcenter else 0.0)) * efficiency / 100.0
                if working > 0 and workcenter:
                    plannedvar += working * workcenter.costs_hour / 60.0
                    plannedfixed += ((workcenter.time_start + workcenter.time_stop)
                                     * efficiency / 100.0 * workcenter.costs_hour_fixed / 60.0)
                elif workcenter:
                    plannedfixed += workorder.duration_expected * workcenter.costs_hour_fixed / 60.0
            for move in production.move_finished_ids.filtered(lambda r: r.state != 'cancel'):
                plannedreceipt += move.product_id.standard_price * move.product_qty
            byproduct = byproduct_unit = 0.0
            if plannedreceipt > 0.0:
                byproduct = plannedreceipt - production.std_prod_cost * qty
                byproduct_unit = byproduct / qty
            production.planned_byproduct_amount = byproduct
            production.planned_byproduct_amount_unit = byproduct_unit
            production.planned_mat_cost = plannedmat
            production.planned_mat_cost_unit = plannedmat / qty
            production.planned_var_cost = plannedvar
            production.planned_var_cost_unit = plannedvar / qty
            production.planned_fixed_cost = plannedfixed
            production.planned_fixed_cost_unit = plannedfixed / qty
            production.planned_direct_cost = plannedvar + plannedfixed + plannedmat - byproduct
            production.planned_direct_cost_unit = production.planned_direct_cost / qty

    def action_confirm(self):
        res = super().action_confirm()
        self._apply_planned_costs()
        return res

    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        # Odoo 19 replaced _generate_backorder_productions with _split_productions.
        productions = super()._split_productions(
            amounts=amounts, cancel_remaining_qty=cancel_remaining_qty, set_consumed_qty=set_consumed_qty)
        productions._apply_planned_costs()
        return productions

    # --- actual costs ---------------------------------------------------------
    @api.depends('move_raw_ids.state', 'product_id', 'qty_producing', 'product_qty')
    def _compute_actual_material_cost(self):
        for production in self:
            matamount = 0.0
            for move in production.move_raw_ids.filtered(lambda r: r.state == 'done'):
                matamount += move.product_id.standard_price * move.product_qty
            qty_produced = production._get_qty_produced()
            production.mat_cost = matamount
            production.mat_cost_unit = matamount / qty_produced

    @api.depends('move_finished_ids.state', 'product_id', 'qty_producing', 'product_qty', 'std_prod_cost')
    def _compute_actual_by_product_amount(self):
        for production in self:
            receiptamount = 0.0
            for move in production.move_finished_ids.filtered(lambda r: r.state == 'done'):
                receiptamount += move.product_id.standard_price * move.product_qty
            qty_produced = production._get_qty_produced()
            amount = unit = 0.0
            if receiptamount > 0.0:
                amount = receiptamount - production.std_prod_cost * qty_produced
                unit = amount / qty_produced
            production.by_product_amount = amount
            production.by_product_amount_unit = unit

    @api.depends('workorder_ids.time_ids', 'workorder_ids.time_ids.overall_duration',
                 'product_id', 'qty_producing', 'product_qty', 'by_product_amount', 'mat_cost')
    def _compute_actual_costs(self):
        for production in self:
            varamount = fixedamount = 0.0
            for workorder in production.workorder_ids:
                workcenter = workorder.workcenter_id
                for time in workorder.time_ids:
                    if time.overall_duration:
                        varamount += time.working_duration * workcenter.costs_hour / 60.0
                        fixedamount += (time.setup_duration + time.teardown_duration) * workcenter.costs_hour_fixed / 60.0
                    else:
                        varamount += time.duration * workcenter.costs_hour / 60.0
            qty_produced = production._get_qty_produced()
            production.var_cost = varamount
            production.var_cost_unit = varamount / qty_produced
            production.fixed_cost = fixedamount
            production.fixed_cost_unit = fixedamount / qty_produced
            production.direct_cost = fixedamount + varamount + production.mat_cost - production.by_product_amount
            production.direct_cost_unit = production.direct_cost / qty_produced

    # --- delta costs ----------------------------------------------------------
    @api.depends('mat_cost', 'var_cost', 'fixed_cost', 'direct_cost', 'by_product_amount',
                 'planned_mat_cost', 'planned_var_cost', 'planned_fixed_cost',
                 'planned_direct_cost', 'planned_byproduct_amount')
    def _compute_delta_costs(self):
        for production in self:
            production.delta_mat_cost = production.mat_cost - production.planned_mat_cost
            production.delta_var_cost = production.var_cost - production.planned_var_cost
            production.delta_fixed_cost = production.fixed_cost - production.planned_fixed_cost
            production.delta_direct_cost = production.direct_cost - production.planned_direct_cost
            production.delta_byproduct = production.by_product_amount - production.planned_byproduct_amount

    # --- WIP ------------------------------------------------------------------
    @api.depends('state', 'var_cost', 'mat_cost', 'fixed_cost')
    def _compute_wip_amount(self):
        for production in self:
            if production.state != 'done':
                production.wip_amount = production.mat_cost + production.var_cost + production.fixed_cost
            else:
                production.wip_amount = 0.0
