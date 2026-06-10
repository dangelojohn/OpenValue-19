# -*- coding: utf-8 -*-

from datetime import date

from odoo import fields, models, _


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    direct_cost = fields.Boolean('Direct Cost Posted', copy=False, default=False)

    def _create_or_update_analytic_entry(self):
        """Suppress the native mrp_account analytic posting; this module posts
        its own standard-costing analytic lines instead."""
        return True

    def button_finish(self):
        res = super().button_finish()
        for record in self:
            if record.state == 'done' and not record.direct_cost:
                record._direct_cost_postings()
                record.direct_cost = True
        return res

    def _direct_cost_postings(self):
        for record in self:
            total_working_duration = 0.0
            total_fixed_duration = 0.0
            workcenter = record.workcenter_id
            desc_wo = '%s-%s-%s' % (record.production_id.name, workcenter.name, record.name)
            last_time = self.env['mrp.workcenter.productivity'].search(
                [('workorder_id', '=', record.id), ('date_end', '!=', False)],
                order="date_end desc", limit=1)
            final_date = last_time.date_end.date() if last_time else date.today()
            # In Odoo 19 the MO no longer carries analytic_account_id; the work
            # center analytic account is authoritative for direct WO costs.
            analytic_account = workcenter.analytic_account_id
            distribution = {analytic_account.id: 100} if analytic_account else False
            for time in record.time_ids:
                if time.overall_duration:
                    total_working_duration += time.working_duration
                    total_fixed_duration += time.setup_duration + time.teardown_duration
                else:
                    total_working_duration += time.duration
            amount_variable = round((total_working_duration * workcenter.costs_hour) / 60.0, 2)
            amount_fixed = round((total_fixed_duration * workcenter.costs_hour_fixed) / 60.0, 2)
            if not (amount_variable or amount_fixed):
                continue
            company = record.production_id.company_id
            if workcenter.wc_type == "H":
                variable_account = company.labour_cost_account_id
                fixed_account = company.labour_fixed_cost_account_id
            else:
                variable_account = company.machine_run_cost_account_id
                fixed_account = company.machine_run_fixed_cost_account_id
            wip_account = record.production_id.product_id.property_stock_production.valuation_account_id
            move = self.env['account.move'].create({
                'journal_id': company.manufacturing_journal_id.id,
                'date': final_date,
                'ref': desc_wo,
                'company_id': workcenter.company_id.id,
                'manufacture_order_id': record.production_id.id,
            })
            AML = self.env['account.move.line'].with_context(check_move_validity=False)
            if amount_variable:
                AML.create({
                    'move_id': move.id,
                    'account_id': variable_account.id,
                    'product_id': record.production_id.product_id.id,
                    'name': " ".join((_("Direct Variable Costs"), record.name)),
                    'quantity': record.qty_output_wo,
                    'product_uom_id': record.production_id.product_uom_id.id,
                    'credit': amount_variable,
                    'debit': 0.0,
                })
                AML.create({
                    'move_id': move.id,
                    'account_id': wip_account.id,
                    'analytic_distribution': distribution,
                    'product_id': record.production_id.product_id.id,
                    'name': " ".join((_("Direct Variable Costs"), record.name)),
                    'quantity': record.qty_output_wo,
                    'product_uom_id': record.production_id.product_uom_id.id,
                    'credit': 0.0,
                    'debit': amount_variable,
                })
            if amount_fixed:
                AML.create({
                    'move_id': move.id,
                    'account_id': fixed_account.id,
                    'product_id': record.production_id.product_id.id,
                    'name': " ".join((_("Direct Fixed Costs"), record.name)),
                    'quantity': record.qty_output_wo,
                    'product_uom_id': record.production_id.product_uom_id.id,
                    'credit': amount_fixed,
                    'debit': 0.0,
                })
                AML.create({
                    'move_id': move.id,
                    'account_id': wip_account.id,
                    'analytic_distribution': distribution,
                    'product_id': record.production_id.product_id.id,
                    'name': " ".join((_("Direct Fixed Costs"), record.name)),
                    'quantity': record.qty_output_wo,
                    'product_uom_id': record.production_id.product_uom_id.id,
                    'credit': 0.0,
                    'debit': amount_fixed,
                })
            # Post once per work order regardless of which cost components exist
            # (the v16 bug posted only when a fixed amount was present).
            move.action_post()
