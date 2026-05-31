# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_compare, float_is_zero, float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    
    # standard unit costs
    std_prod_cost = fields.Float('Current Standard Cost', digits='Product Price', compute='calculate_standard_costs', store=True, aggregator="avg")
    std_mat_cost = fields.Float('Standard Material Unit Cost', digits='Product Price', compute='calculate_standard_costs', store=True, aggregator="avg")
    std_var_cost = fields.Float('Standard Direct Variable Unit Cost', digits='Product Price', compute='calculate_standard_costs', store=True, aggregator="avg")
    std_fixed_cost = fields.Float('Standard Direct Fixed Unit Cost', digits='Product Price', compute='calculate_standard_costs', store=True, aggregator="avg")
    std_direct_cost = fields.Float('Standard Direct Unit Cost', digits='Product Price', compute='calculate_standard_costs', store=True, aggregator="avg")
    # compute method was 'calculate_standard_by_product_amount', which is not
    # defined anywhere (v19 hard-errors at registry load on a missing compute);
    # std_byproduct_amount is actually assigned by calculate_standard_costs.
    std_byproduct_amount = fields.Float('Standard ByProduct Amount', digits='Product Price', compute='calculate_standard_costs', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)

    # MO-level analytic account. v19 removed mrp.production.analytic_account_id
    # (replaced upstream by distribution mechanics); this module re-adds it so the
    # v16 "MO account overrides workcenter account" precedence is preserved. When
    # left empty the postings fall back to the workcenter analytic account, exactly
    # as before. [Migration decision A - confirm intent.]
    analytic_account_id = fields.Many2one(
        'account.analytic.account', "Analytic Account", copy=False,
        groups="analytic.group_analytic_accounting")
     
    # planned costs
    planned_mat_cost = fields.Float('Planned Material Cost', digits='Product Price', compute='calculate_planned_costs', store=True)
    planned_mat_cost_unit = fields.Float('Planned Material Unit Cost', digits='Product Price', compute='calculate_planned_costs', store=True, aggregator="avg")
    planned_var_cost = fields.Float('Planned Direct Variable Cost', digits='Product Price', compute='calculate_planned_costs', store=True)
    planned_var_cost_unit = fields.Float('Planned Direct Variable Unit Cost', digits='Product Price', compute='calculate_planned_costs', store=True, aggregator="avg")
    planned_fixed_cost = fields.Float('Planned Direct Fixed Cost', digits='Product Price', compute='calculate_planned_costs', store=True)
    planned_fixed_cost_unit = fields.Float('Planned Direct Fixed Unit Cost', digits='Product Price', compute='calculate_planned_costs', store=True, aggregator="avg")
    planned_direct_cost = fields.Float('Planned Direct Cost', digits='Product Price', compute='calculate_planned_costs', store=True)
    planned_direct_cost_unit = fields.Float('Planned Direct Unit Cost', digits='Product Price', compute='calculate_planned_costs', store=True, aggregator="avg")
    # compute pointed at the undecorated helper '_calculate_planned_costs'; align
    # with the siblings on the decorated 'calculate_planned_costs'.
    planned_byproduct_amount = fields.Float('Planned ByProduct Amount', digits='Product Price', compute='calculate_planned_costs', store=True)
    planned_byproduct_amount_unit = fields.Float('Planned ByProduct Unit Amount', digits='Product Price', compute='calculate_planned_costs', store=True, aggregator="avg")
    # actual costs
    mat_cost = fields.Float('Actual Components Cost', digits='Product Price', compute='calculate_actual_material_cost', store=True)
    mat_cost_unit = fields.Float('Actual Components Unit Cost', digits='Product Price', compute='calculate_actual_material_cost', store=True, aggregator="avg")
    var_cost = fields.Float('Actual Direct Variable Cost', digits='Product Price', compute='calculate_actual_costs', store=True)
    var_cost_unit = fields.Float('Actual Direct Variable Unit Cost', digits='Product Price', compute='calculate_actual_costs', store=True, aggregator="avg")
    fixed_cost = fields.Float('Actual Direct Fixed Cost', digits='Product Price', compute='calculate_actual_costs', store=True)
    fixed_cost_unit = fields.Float('Actual Direct Fixed Unit Cost', digits='Product Price', compute='calculate_actual_costs', store=True, aggregator="avg")
    direct_cost = fields.Float('Actual Full Direct Cost', digits='Product Price', compute='calculate_actual_costs', store=True)
    direct_cost_unit = fields.Float('Actual Full Direct Unit Cost', digits='Product Price', compute='calculate_actual_costs', store=True, aggregator="avg")
    by_product_amount = fields.Float('Actual ByProduct Amount', digits='Product Price', compute='calculate_actual_by_product_amount', store=True)
    by_product_amount_unit = fields.Float('Actual ByProduct Unit Amount', digits='Product Price', compute='calculate_actual_by_product_amount', store=True, aggregator="avg")
    # delta costs = actual - planned
    delta_mat_cost = fields.Float('Delta Components Cost', digits='Product Price', compute='calculate_delta_costs', store=True)
    delta_var_cost = fields.Float('Delta Direct Variable Cost', digits='Product Price', compute='calculate_delta_costs', store=True)
    delta_fixed_cost = fields.Float('Delta Direct Fixed Cost', digits='Product Price', compute='calculate_delta_costs', store=True)
    delta_direct_cost = fields.Float('Delta Direct Cost', digits='Product Price', compute='calculate_delta_costs', store=True)
    delta_byproduct = fields.Float('Delta ByProduct Amount', digits='Product Price', compute='calculate_delta_costs', store=True)
    
    wip_amount = fields.Float('WIP Amount', digits='Product Price',  compute='calculate_wip_amount', store=True)
    
    def _get_qty_produced(self):
        qty_produced = 1.0
        for production in self:
            if production.product_id and production.product_qty:
                if not production.qty_producing == 0.0:
                    qty_produced = production.product_uom_id._compute_quantity(production.qty_producing, production.product_id.product_tmpl_id.uom_id)
                else:
                    qty_produced = production.product_uom_qty
        return qty_produced

    # standard costs calculation
    @api.depends('bom_id', 'product_uom_qty', 'product_id.standard_price',
                 'bom_id.bom_line_ids', 'bom_id.operation_ids', 'bom_id.byproduct_ids')
    def calculate_standard_costs(self):
        for production in self:
            # accumulators reset per record (were initialised once before the loop,
            # leaking running totals across a multi-MO recordset).
            costmat = costvar = costfixed = byproductamount = 0.0
            bom = production.bom_id
            # guard the divisors (bom.product_qty / product_uom_qty) against zero.
            if bom and bom.product_qty and production.product_uom_qty:
                result, result2 = bom.explode(production.product_id, 1)
                for sbom, sbom_data in result2:
                    costmat += sbom.product_id.standard_price * sbom_data['qty'] / bom.product_qty
                for operation in bom.operation_ids:
                    workcenter = operation.workcenter_id
                    # skip operations whose workcenter would divide by zero.
                    if not workcenter.capacity or not workcenter.time_efficiency:
                        continue
                    cycle_number = float_round(production.product_uom_qty / workcenter.capacity, precision_digits=0, rounding_method='UP')
                    time_cycle = operation.time_cycle
                    costvar += (((cycle_number * time_cycle * 100.0 / workcenter.time_efficiency) / 60) * workcenter.costs_hour) / production.product_uom_qty / bom.product_qty
                    costfixed += ((workcenter.time_stop + workcenter.time_start) * workcenter.costs_hour_fixed / 60) / production.product_uom_qty
                for byproduct_id in bom.byproduct_ids:
                    byproductamount += byproduct_id.product_id.standard_price * byproduct_id.product_qty / bom.product_qty
            # assigned on every record / every path (v19 ORM strictness).
            production.std_prod_cost = production.product_id.standard_price
            production.std_byproduct_amount = byproductamount
            production.std_mat_cost = costmat
            production.std_var_cost = costvar
            production.std_fixed_cost = costfixed
            production.std_direct_cost = costvar + costfixed + costmat - byproductamount
  
    # planned costs calculation
    @api.depends('move_raw_ids', 'move_raw_ids.product_qty', 'move_raw_ids.state',
                 'move_finished_ids', 'move_finished_ids.product_qty', 'move_finished_ids.state',
                 'workorder_ids', 'workorder_ids.duration_expected',
                 'product_uom_qty', 'std_prod_cost', 'product_id.standard_price')
    def calculate_planned_costs(self):
        # Was gated on state == "confirmed", so other records were left unassigned
        # (v19 ORM hard-errors on a stored compute that skips records). It now
        # assigns every planned_* field on every record. The figures derive from
        # planning inputs (planned move qty, duration_expected, standard price), so
        # they remain "planned" values even when recomputed later in the lifecycle.
        self._calculate_planned_costs()

    def _calculate_planned_costs(self):
        for production in self:
            # accumulators reset per record (were initialised once before the loop).
            plannedmatamount = plannedvaramount = plannedfixedamount = plannedreceiptamount = 0.0
            # raw materials
            raw_moves = production.move_raw_ids.filtered(lambda r: r.state != 'cancel')
            for move in raw_moves:
                plannedmatamount += move.product_id.standard_price * move.product_qty
            # workorders
            for workorder in production.workorder_ids:
                workcenter = workorder.workcenter_id
                duration_expected_working = (workorder.duration_expected - workcenter.time_start - workcenter.time_stop) * workcenter.time_efficiency / 100.0
                if duration_expected_working > 0:
                    plannedvaramount += duration_expected_working * workcenter.costs_hour / 60
                    plannedfixedamount += (workcenter.time_start + workcenter.time_stop) * workcenter.time_efficiency / 100.0 * workcenter.costs_hour_fixed / 60
                else:
                    plannedfixedamount += workorder.duration_expected * workcenter.costs_hour_fixed / 60
            # by products
            finished_moves = production.move_finished_ids.filtered(lambda r: r.state != 'cancel')
            for move in finished_moves:
                plannedreceiptamount += move.product_id.standard_price * move.product_qty
            qty = production.product_uom_qty
            # assigned on every path; divisors guarded against zero qty.
            production.planned_byproduct_amount = 0.0
            production.planned_byproduct_amount_unit = 0.0
            if qty and plannedreceiptamount > 0.0:
                production.planned_byproduct_amount = plannedreceiptamount - production.std_prod_cost * qty
                production.planned_byproduct_amount_unit = production.planned_byproduct_amount / qty
            production.planned_mat_cost = plannedmatamount
            production.planned_mat_cost_unit = plannedmatamount / qty if qty else 0.0
            production.planned_var_cost = plannedvaramount
            production.planned_var_cost_unit = plannedvaramount / qty if qty else 0.0
            production.planned_fixed_cost = plannedfixedamount
            production.planned_fixed_cost_unit = plannedfixedamount / qty if qty else 0.0
            production.planned_direct_cost = plannedvaramount + plannedfixedamount + production.planned_mat_cost - production.planned_byproduct_amount
            production.planned_direct_cost_unit = production.planned_direct_cost / qty if qty else 0.0
    
    # recalculate planned costs
    # v19 replaced _generate_backorder_productions(close_mo) with
    # _split_productions(amounts, cancel_remaining_qty, set_consumed_qty); the old
    # override never fired. Re-home onto the new hook, keeping the v16 behaviour of
    # recomputing planned costs across every MO in the procurement group.
    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        productions = super()._split_productions(
            amounts=amounts, cancel_remaining_qty=cancel_remaining_qty,
            set_consumed_qty=set_consumed_qty)
        self.procurement_group_id.mrp_production_ids._calculate_planned_costs()
        return productions
    
    # actual costs calculation
    @api.depends('move_raw_ids.state','move_raw_ids.product_qty','product_id','qty_producing','product_qty')
    def calculate_actual_material_cost(self):
        for production in self:
            # accumulator reset per record.
            matamount = 0.0
            moves = production.move_raw_ids.filtered(lambda r: r.state == 'done')
            for move in moves:
                matamount += move.product_id.standard_price * move.product_qty
            qty_produced = production._get_qty_produced()  # floored at 1.0
            production.mat_cost = matamount
            production.mat_cost_unit = matamount/qty_produced
   
    @api.depends('move_finished_ids.state','move_finished_ids.product_qty','product_id','qty_producing','product_qty','std_prod_cost')
    def calculate_actual_by_product_amount(self):
        for production in self:
            # accumulator reset per record.
            receiptamount = 0.0
            moves = production.move_finished_ids.filtered(lambda r: r.state == 'done')
            for move in moves:
                receiptamount += move.product_id.standard_price * move.product_qty
            qty_produced = production._get_qty_produced()  # floored at 1.0
            # initialise on every path so the fields are always assigned (v19 ORM).
            production.by_product_amount = 0.0
            production.by_product_amount_unit = 0.0
            if receiptamount > 0.0:
                production.by_product_amount = receiptamount - production.std_prod_cost * qty_produced
                production.by_product_amount_unit = production.by_product_amount/qty_produced
    
    @api.depends('workorder_ids.time_ids','product_id','qty_producing','product_qty','by_product_amount','mat_cost')
    def calculate_actual_costs(self):
        for production in self:
            # accumulators reset per record.
            varamount = 0.0
            fixedamount = 0.0
            for workorder in production.workorder_ids:
                for time in workorder.time_ids:
                    if time.overall_duration:
                        varamount += time.working_duration * workorder.workcenter_id.costs_hour / 60
                        fixedamount += (time.setup_duration + time.teardown_duration) * workorder.workcenter_id.costs_hour_fixed / 60
                    else:
                        varamount += time.duration * workorder.workcenter_id.costs_hour / 60
            qty_produced = production._get_qty_produced()
            production.var_cost = varamount 
            production.var_cost_unit = varamount/qty_produced
            production.fixed_cost = fixedamount
            production.fixed_cost_unit = fixedamount/qty_produced
            production.direct_cost = fixedamount + varamount + production.mat_cost - production.by_product_amount
            production.direct_cost_unit = production.direct_cost/qty_produced
    
    # delta costs calculation
    @api.depends('mat_cost_unit','var_cost_unit','direct_cost_unit','by_product_amount')
    def calculate_delta_costs(self):
        for production in self:
            production.delta_mat_cost = production.mat_cost - production.planned_mat_cost
            production.delta_var_cost = production.var_cost - production.planned_var_cost
            production.delta_fixed_cost = production.fixed_cost - production.planned_fixed_cost
            production.delta_direct_cost = production.direct_cost - production.planned_direct_cost
            production.delta_byproduct = production.by_product_amount - production.planned_byproduct_amount
    
    # WIP calculation
    @api.depends('state','var_cost','mat_cost','fixed_cost')
    def calculate_wip_amount(self):
        wipamount = 0.0
        for production in self:
            if production.state != 'done':
                wipamount = production.mat_cost + production.var_cost + production.fixed_cost
            production.wip_amount = wipamount 
