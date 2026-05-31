# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from datetime import date


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    closure_state = fields.Boolean('Financial Closure', copy=False, default=False)
    # overheads
    ovh_var_direct_cost = fields.Float('OVH Variable Direct Cost', digits='Product Price', readonly=True, copy=False)
    ovh_fixed_direct_cost = fields.Float('OVH Fixed Direct Cost', digits='Product Price', readonly=True, copy=False)
    ovh_product_cost = fields.Float('OVH Finished Product Cost', digits='Product Price', readonly=True, copy=False)
    ovh_components_cost = fields.Float('OVH Components Cost', digits='Product Price', readonly=True, copy=False)
    industrial_cost = fields.Float('Actual Full Industrial Cost', digits='Product Price', readonly=True, copy=False)
    industrial_cost_unit = fields.Float(' Actual Full Industrial Unit Cost', digits='Product Price', aggregator="avg", readonly=True, copy=False)

    def button_mark_done(self):
        action = super().button_mark_done()
        for production in self:
            # super() may return a wizard (backorder / immediate production) and
            # leave the MO not actually done; only purge analytic lines once done.
            if production.state != 'done':
                continue
            # v19: the analytic-line links are plural recordsets
            # (stock.move.analytic_account_line_ids, workorder.mo_analytic_account_line_ids);
            # operate on them directly rather than re-browsing a single id.
            production.move_raw_ids.analytic_account_line_ids.sudo().unlink()
            production.workorder_ids.mo_analytic_account_line_ids.sudo().unlink()
        return action

    def button_closure(self):
        for record in self:
            # Idempotency guard: re-running would post a second full set of variance
            # + overhead entries. Stop before posting anything.
            if record.closure_state:
                raise UserError(_(
                    "Manufacturing Order %s is already financially closed.",
                    record.display_name))
            # Fail fast on incomplete accounting configuration rather than leaving a
            # half-posted batch behind.
            record._check_closure_configuration()
            qty_produced = record._get_qty_produced()
            # variances
            record._planned_variance_postings(qty_produced)
            record._material_costs_variance_postings(qty_produced)
            record._direct_costs_variance_postings(qty_produced)
            # overheads
            record._wc_ovh_analytic_postings()
            record._bom_ovh_analytic_postings()
            record.industrial_cost = record.direct_cost + record.ovh_var_direct_cost + record.ovh_fixed_direct_cost + record.ovh_product_cost + record.ovh_components_cost
            record.industrial_cost_unit = record.industrial_cost / qty_produced
            record.closure_state = True
        return True

    def _check_closure_configuration(self):
        self.ensure_one()
        company = self.company_id
        missing = []
        if not company.manufacturing_journal_id:
            missing.append(_("Manufacturing Journal"))
        if not company.planned_variances_account_id:
            missing.append(_("Planned Variance Cost Account"))
        if not company.material_variances_account_id:
            missing.append(_("Components Variance Cost Account"))
        if not company.other_variances_account_id:
            missing.append(_("Direct Variance Cost Account"))
        if missing:
            raise UserError(_(
                "Cannot close Manufacturing Order %(mo)s: the following accounting "
                "settings are not configured on company %(company)s:\n- %(items)s",
                mo=self.display_name,
                company=company.display_name,
                items="\n- ".join(missing),
            ))

    def _get_final_date(self):
        final_date = False
        for record in self:
            if record.date_actual_finished_wo:
                final_date = record.date_actual_finished_wo.date()
            else:
                final_date = date.today()
        return final_date

    # production planned variance costs posting
    def _planned_variance_postings(self, quantity):
        standard_cost = planned_cost = 0.0
        for record in self:
            final_date = record._get_final_date()
            standard_cost = record.std_prod_cost
            planned_cost = record.planned_direct_cost_unit
            delta = (planned_cost - standard_cost) * quantity
            desc_bom = str(record.name)
            if delta < 0.0:
                id_created_header = self.env['account.move'].create({
                'journal_id' : record.company_id.manufacturing_journal_id.id,
                'date': final_date,
                'ref' : "Planned Costs Variance",
                'company_id': record.company_id.id,
                'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.planned_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': - delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_account_id.id,
                    'analytic_distribution': {record.bom_id.costs_planned_variances_analytic_account_id.id: 100},
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': - delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
            elif delta > 0.0:
                id_created_header = self.env['account.move'].create({
                'journal_id' : record.company_id.manufacturing_journal_id.id,
                'date': final_date,
                'ref' : "Planned Costs Variance",
                'company_id': record.company_id.id,
                'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_account_id.id,
                    'analytic_distribution': {record.bom_id.costs_planned_variances_analytic_account_id.id: 100},
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.planned_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
        return True

    # production material and by product variance costs posting
    def _material_costs_variance_postings(self, quantity):
        for record in self:
            # accumulators reset per record (were initialised once before the loop,
            # leaking running totals across a multi-MO recordset).
            mat_actual_amount = mat_planned_amount = matamount = receiptamount = by_product_amount = 0.0
            final_date = record._get_final_date()
            # v19: product.type no longer has 'product'; storable goods are flagged
            # by is_storable.
            raw_moves = record.move_raw_ids.filtered(lambda r: (r.state == 'done' and r.product_id.is_storable))
            for move in raw_moves:
                matamount += move.product_id.standard_price * move.product_qty
            finished_moves = record.move_finished_ids.filtered(lambda r: (r.state == 'done' and r.product_id.is_storable))
            for move in finished_moves:
                receiptamount += move.product_id.standard_price * move.product_qty
            if receiptamount > 0.0:
                by_product_amount = receiptamount - record.std_prod_cost * quantity
            mat_actual_amount = matamount - by_product_amount
            mat_planned_amount = (record.planned_mat_cost_unit - record.planned_byproduct_amount_unit) * quantity
            delta = mat_actual_amount - mat_planned_amount
            desc_bom = str(record.name)
            if delta < 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Material and By Products Variance",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.material_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': - delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_account_id.id,
                    'analytic_distribution': {record.bom_id.costs_material_variances_analytic_account_id.id: 100},
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': - delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
            elif delta > 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Material and By Products Variance",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_account_id.id,
                    'analytic_distribution': {record.bom_id.costs_material_variances_analytic_account_id.id: 100},
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.material_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
        return True

    # production direct variance costs posting
    def _direct_costs_variance_postings(self, quantity):
        for record in self:
            # accumulators reset per record (see _material_costs_variance_postings).
            direct_actual_amount = direct_planned_amount = 0.0
            final_date = record._get_final_date()
            direct_actual_amount = (record.var_cost_unit + record.fixed_cost_unit) * quantity
            direct_planned_amount =  (record.planned_var_cost_unit + record.planned_fixed_cost_unit) * quantity
            delta = direct_actual_amount - direct_planned_amount
            desc_bom = str(record.name)
            if delta < 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Direct Costs Variance",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.other_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': - delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_account_id.id,
                    'analytic_distribution': {record.bom_id.costs_direct_variances_analytic_account_id.id: 100},
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': - delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
            elif delta > 0.0:
                id_created_header = self.env['account.move'].create({
                    'journal_id' : record.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref' : "Direct Costs Variance",
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
                id_credit_item = self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.product_id.property_stock_production.valuation_account_id.id,
                    'analytic_distribution': {record.bom_id.costs_direct_variances_analytic_account_id.id: 100},
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': delta,
                    'debit': 0.0,
                    #'manufacture_order_id': record.id,
                })
                id_debit_item= self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'move_id' : id_created_header.id,
                    'account_id': record.company_id.other_variances_account_id.id,
                    'product_id': record.product_id.id,
                    'name' : desc_bom,
                    'quantity': quantity,
                    'product_uom_id': record.product_uom_id.id,
                    'credit': 0.0,
                    'debit': delta,
                    #'manufacture_order_id': record.id,
                })
                id_created_header.action_post()
        return True

    def _wc_ovh_analytic_postings(self):
        for record in self:
            final_date = record._get_final_date()
            # per-record running totals for the stored fields
            total_varamount = 0.0
            total_fixedamount = 0.0
            for workorder in record.workorder_ids:
                # per-workorder amounts: reset each iteration so the analytic line
                # posted for a workorder reflects ONLY that workorder. (Previously
                # these accumulated across workorders but were posted inside the
                # loop, so WO2 posted WO1+WO2, WO3 posted WO1+WO2+WO3, etc.)
                varamount = 0.0
                fixedamount = 0.0
                desc_wo = str(record.name) + '-' + str(workorder.workcenter_id.name) + '-' + str(workorder.name)
                for time in workorder.time_ids:
                    if time.overall_duration:
                        varamount += time.working_duration * workorder.workcenter_id.costs_hour / 60 * workorder.workcenter_id.costs_overhead_variable_percentage / 100
                        fixedamount += (time.setup_duration + time.teardown_duration) * workorder.workcenter_id.costs_hour_fixed / 60 * workorder.workcenter_id.costs_overhead_fixed_percentage / 100
                    else:
                        varamount += time.duration * workorder.workcenter_id.costs_hour / 60 * workorder.workcenter_id.costs_overhead_variable_percentage / 100
                # fixed direct overhead cost posting
                if fixedamount:
                    id_created= self.env['account.analytic.line'].create({
                        'name': desc_wo,
                        'account_id': workorder.workcenter_id.analytic_account_id.id,
                        'ref': "OVH fixed direct costs",
                        'date': final_date,
                        'product_id': record.product_id.id,
                        'amount': - fixedamount,
                        'unit_amount': workorder.qty_output_wo,
                        'product_uom_id': record.product_uom_id.id,
                        'company_id': workorder.workcenter_id.company_id.id,
                        'manufacture_order_id': record.id,
                    })
                # variable direct overhead cost posting
                if varamount:
                    id_created= self.env['account.analytic.line'].create({
                        'name': desc_wo,
                        'account_id': workorder.workcenter_id.analytic_account_id.id,
                        'ref': "OVH variable direct costs",
                        'date': final_date,
                        'product_id': record.product_id.id,
                        'amount': - varamount,
                        'unit_amount': workorder.qty_output_wo,
                        'product_uom_id': record.product_uom_id.id,
                        'company_id': workorder.workcenter_id.company_id.id,
                        'manufacture_order_id': record.id,
                    })
                total_varamount += varamount
                total_fixedamount += fixedamount
            record.ovh_var_direct_cost = total_varamount
            record.ovh_fixed_direct_cost = total_fixedamount
        return True

    def _bom_ovh_analytic_postings(self):
        ovhproductcost = ovhcomponentscost = 0.0
        for record in self:
            final_date = record._get_final_date()
            desc_bom = str(record.name)
            ovhproductcost = record.direct_cost * record.bom_id.costs_overhead_product_percentage / 100
            ovhcomponentscost = record.mat_cost * record.bom_id.costs_overhead_components_percentage / 100
            # overhead product cost posting
            if ovhproductcost:
                id_created= self.env['account.analytic.line'].create({
                    'name': desc_bom,
                    'account_id': record.bom_id.overhead_analytic_account_id.id,
                    'ref': "OVH production costs",
                    'date': final_date,
                    'product_id': record.product_id.id,
                    'amount': - ovhproductcost,
                    'unit_amount': record.product_qty,
                    'product_uom_id': record.product_uom_id.id,
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
            # overhead components cost posting
            if ovhcomponentscost:
                id_created= self.env['account.analytic.line'].create({
                    'name': desc_bom,
                    'account_id': record.bom_id.overhead_analytic_account_id.id,
                    'ref': "OVH components costs",
                    'date': final_date,
                    'product_id': record.product_id.id,
                    'amount': - ovhcomponentscost,
                    'unit_amount': record.product_qty,
                    'product_uom_id': record.product_uom_id.id,
                    'company_id': record.company_id.id,
                    'manufacture_order_id': record.id,
                })
            record.ovh_product_cost = ovhproductcost
            record.ovh_components_cost = ovhcomponentscost
        return True

