# -*- coding: utf-8 -*-

from datetime import date

from odoo import fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    closure_state = fields.Boolean('Financial Closure', copy=False, default=False)
    # overheads
    ovh_var_direct_cost = fields.Float('OVH Variable Direct Cost', digits='Product Price', readonly=True, copy=False)
    ovh_fixed_direct_cost = fields.Float('OVH Fixed Direct Cost', digits='Product Price', readonly=True, copy=False)
    ovh_product_cost = fields.Float('OVH Finished Product Cost', digits='Product Price', readonly=True, copy=False)
    ovh_components_cost = fields.Float('OVH Components Cost', digits='Product Price', readonly=True, copy=False)
    industrial_cost = fields.Float('Actual Full Industrial Cost', digits='Product Price', readonly=True, copy=False)
    industrial_cost_unit = fields.Float('Actual Full Industrial Unit Cost', digits='Product Price', aggregator="avg", readonly=True, copy=False)

    # -------------------------------------------------------------------------
    def button_mark_done(self):
        res = super().button_mark_done()
        for production in self:
            # super() may return a wizard (immediate production / backorder);
            # only clean up native analytic lines once the MO is really done.
            if production.state != 'done':
                continue
            production.move_raw_ids.analytic_account_line_ids.sudo().unlink()
            (production.workorder_ids.mo_analytic_account_line_ids
             | production.workorder_ids.wc_analytic_account_line_ids).sudo().unlink()
        return res

    def _get_final_date(self):
        self.ensure_one()
        if self.date_actual_finished_wo:
            return self.date_actual_finished_wo.date()
        return date.today()

    def _check_closure_config(self):
        """Fail fast before any posting if the financial configuration is
        incomplete, to avoid a half-posted closure."""
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
        if not self.product_id.property_stock_production.valuation_account_id:
            missing.append(_("Production Location Valuation Account"))
        if missing:
            raise UserError(_(
                "Cannot close the manufacturing order %(name)s: the following "
                "configuration is missing:\n- %(items)s",
                name=self.name, items="\n- ".join(missing)))

    def button_closure(self):
        for record in self:
            if record.closure_state:
                raise UserError(_(
                    "Manufacturing order %s has already been financially closed.", record.name))
            record._check_closure_config()
            qty_produced = record._get_qty_produced()
            # variances
            record._planned_variance_postings(qty_produced)
            record._material_costs_variance_postings(qty_produced)
            record._direct_costs_variance_postings(qty_produced)
            # overheads
            record._wc_ovh_analytic_postings()
            record._bom_ovh_analytic_postings()
            record.industrial_cost = (record.direct_cost + record.ovh_var_direct_cost
                                      + record.ovh_fixed_direct_cost + record.ovh_product_cost
                                      + record.ovh_components_cost)
            record.industrial_cost_unit = record.industrial_cost / qty_produced
            record.closure_state = True
        return True

    # --- shared variance posting helper --------------------------------------
    def _post_variance_entry(self, ref, variance_account, analytic_account, delta, quantity, final_date):
        """Post a balanced 2-line variance entry.

        ``delta`` is (actual - planned): a negative delta credits the variance
        account and debits the production valuation account; a positive delta
        does the reverse.  The valuation-side line always carries the analytic
        distribution and the move always back-references the MO.
        """
        self.ensure_one()
        if not delta:
            return
        valuation_account = self.product_id.property_stock_production.valuation_account_id
        distribution = {analytic_account.id: 100} if analytic_account else False
        move = self.env['account.move'].create({
            'journal_id': self.company_id.manufacturing_journal_id.id,
            'date': final_date,
            'ref': ref,
            'company_id': self.company_id.id,
            'manufacture_order_id': self.id,
        })
        AML = self.env['account.move.line'].with_context(check_move_validity=False)
        amount = abs(delta)
        variance_vals = {
            'move_id': move.id,
            'account_id': variance_account.id,
            'product_id': self.product_id.id,
            'name': ref,
            'quantity': quantity,
            'product_uom_id': self.product_uom_id.id,
        }
        valuation_vals = {
            'move_id': move.id,
            'account_id': valuation_account.id,
            'analytic_distribution': distribution,
            'product_id': self.product_id.id,
            'name': ref,
            'quantity': quantity,
            'product_uom_id': self.product_uom_id.id,
        }
        if delta < 0.0:
            variance_vals.update({'credit': amount, 'debit': 0.0})
            valuation_vals.update({'credit': 0.0, 'debit': amount})
        else:
            valuation_vals.update({'credit': amount, 'debit': 0.0})
            variance_vals.update({'credit': 0.0, 'debit': amount})
        AML.create(variance_vals)
        AML.create(valuation_vals)
        move.action_post()

    def _planned_variance_postings(self, quantity):
        for record in self:
            delta = (record.planned_direct_cost_unit - record.std_prod_cost) * quantity
            record._post_variance_entry(
                _("Planned Costs Variance"),
                record.company_id.planned_variances_account_id,
                record.bom_id.costs_planned_variances_analytic_account_id,
                delta, quantity, record._get_final_date())

    def _material_costs_variance_postings(self, quantity):
        for record in self:
            matamount = receiptamount = 0.0
            raw_moves = record.move_raw_ids.filtered(
                lambda r: r.state == 'done' and r.product_id.is_storable)
            for move in raw_moves:
                matamount += move.product_id.standard_price * move.product_qty
            finished_moves = record.move_finished_ids.filtered(
                lambda r: r.state == 'done' and r.product_id.is_storable)
            for move in finished_moves:
                receiptamount += move.product_id.standard_price * move.product_qty
            by_product_amount = (receiptamount - record.std_prod_cost * quantity) if receiptamount > 0.0 else 0.0
            mat_actual = matamount - by_product_amount
            mat_planned = (record.planned_mat_cost_unit - record.planned_byproduct_amount_unit) * quantity
            record._post_variance_entry(
                _("Material and By Products Variance"),
                record.company_id.material_variances_account_id,
                record.bom_id.costs_material_variances_analytic_account_id,
                mat_actual - mat_planned, quantity, record._get_final_date())

    def _direct_costs_variance_postings(self, quantity):
        for record in self:
            direct_actual = (record.var_cost_unit + record.fixed_cost_unit) * quantity
            direct_planned = (record.planned_var_cost_unit + record.planned_fixed_cost_unit) * quantity
            record._post_variance_entry(
                _("Direct Costs Variance"),
                record.company_id.other_variances_account_id,
                record.bom_id.costs_direct_variances_analytic_account_id,
                direct_actual - direct_planned, quantity, record._get_final_date())

    # --- overhead analytic postings ------------------------------------------
    def _wc_ovh_analytic_postings(self):
        for record in self:
            final_date = record._get_final_date()
            total_var = total_fixed = 0.0
            for workorder in record.workorder_ids:
                workcenter = workorder.workcenter_id
                desc_wo = '%s-%s-%s' % (record.name, workcenter.name, workorder.name)
                wo_var = wo_fixed = 0.0
                for time in workorder.time_ids:
                    if time.overall_duration:
                        wo_var += (time.working_duration * workcenter.costs_hour / 60.0
                                   * workcenter.costs_overhead_variable_percentage / 100.0)
                        wo_fixed += ((time.setup_duration + time.teardown_duration) * workcenter.costs_hour_fixed / 60.0
                                     * workcenter.costs_overhead_fixed_percentage / 100.0)
                    else:
                        wo_var += (time.duration * workcenter.costs_hour / 60.0
                                   * workcenter.costs_overhead_variable_percentage / 100.0)
                if wo_fixed:
                    self.env['account.analytic.line'].create(record._ovh_analytic_vals(
                        desc_wo, workcenter.analytic_account_id, _("OVH fixed direct costs"),
                        final_date, -wo_fixed, workorder.qty_output_wo, workcenter.company_id))
                if wo_var:
                    self.env['account.analytic.line'].create(record._ovh_analytic_vals(
                        desc_wo, workcenter.analytic_account_id, _("OVH variable direct costs"),
                        final_date, -wo_var, workorder.qty_output_wo, workcenter.company_id))
                total_var += wo_var
                total_fixed += wo_fixed
            record.ovh_var_direct_cost = total_var
            record.ovh_fixed_direct_cost = total_fixed

    def _bom_ovh_analytic_postings(self):
        for record in self:
            final_date = record._get_final_date()
            ovhproductcost = record.direct_cost * record.bom_id.costs_overhead_product_percentage / 100.0
            ovhcomponentscost = record.mat_cost * record.bom_id.costs_overhead_components_percentage / 100.0
            if ovhproductcost:
                self.env['account.analytic.line'].create(record._ovh_analytic_vals(
                    record.name, record.bom_id.overhead_analytic_account_id, _("OVH production costs"),
                    final_date, -ovhproductcost, record.product_qty, record.company_id))
            if ovhcomponentscost:
                self.env['account.analytic.line'].create(record._ovh_analytic_vals(
                    record.name, record.bom_id.overhead_analytic_account_id, _("OVH components costs"),
                    final_date, -ovhcomponentscost, record.product_qty, record.company_id))
            record.ovh_product_cost = ovhproductcost
            record.ovh_components_cost = ovhcomponentscost

    def _ovh_analytic_vals(self, name, analytic_account, ref, final_date, amount, unit_amount, company):
        self.ensure_one()
        vals = {
            'name': name,
            'ref': ref,
            'date': final_date,
            'product_id': self.product_id.id,
            'amount': amount,
            'unit_amount': unit_amount,
            'product_uom_id': self.product_uom_id.id,
            'company_id': company.id,
            'manufacture_order_id': self.id,
            'category': 'manufacturing_order',
        }
        if analytic_account:
            vals[analytic_account.plan_id._column_name()] = analytic_account.id
        return vals
