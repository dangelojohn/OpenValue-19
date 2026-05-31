# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from datetime import date


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    direct_cost = fields.Boolean('Direct Cost', copy=False, default=False)

    def _create_or_update_analytic_entry(self):
        return True

    def button_finish(self):
        res = super().button_finish()
        for record in self:
            if record.state == 'done' and not record.direct_cost:
                record._direct_cost_postings()
                record.direct_cost = True
        return res

    # production direct cost posting
    #
    # Fixes applied in migration:
    #   - accumulators (durations) are reset PER workorder, inside `for record in
    #     self:` (were initialised once before the loop -> later workorders summed
    #     prior ones).
    #   - `action_post()` runs whenever the journal entry header was created (was
    #     nested under `if amount_fixed:`, so a workorder with only a variable cost
    #     produced a journal entry that was never posted).
    #   - v19: analytic on the debit lines uses `analytic_distribution` (a dict),
    #     not the removed `analytic_account_id` move-line field.
    #   - v19: production location valuation account is the single
    #     `valuation_account_id` (was `valuation_in_account_id`).
    def _direct_cost_postings(self):
        for record in self:
            total_working_duration = 0.0
            total_fixed_duration = 0.0
            final_date = False
            desc_wo = record.production_id.name + '-' + record.workcenter_id.name + '-' + record.name
            last_time = self.env['mrp.workcenter.productivity'].search(
                [('workorder_id', '=', record.id), ('date_end', '!=', False)],
                order="date_end desc", limit=1)
            if last_time:
                final_date = last_time.date_end.date()
            else:
                final_date = date.today()
            analytic_account = record.production_id.analytic_account_id.id or record.workcenter_id.analytic_account_id.id
            analytic_distribution = {str(analytic_account): 100} if analytic_account else False
            for time in record.time_ids:
                if time.overall_duration:
                    total_working_duration += time.working_duration
                    total_fixed_duration += time.setup_duration + time.teardown_duration
                else:
                    total_working_duration += time.duration
            amount_variable = round((total_working_duration * record.workcenter_id.costs_hour) / 60, 2)
            amount_fixed = round((total_fixed_duration * record.workcenter_id.costs_hour_fixed) / 60, 2)
            if amount_variable or amount_fixed:
                if record.workcenter_id.wc_type == "H":
                    variable_account_id = record.production_id.company_id.labour_cost_account_id
                    fixed_account_id = record.production_id.company_id.labour_fixed_cost_account_id
                else:
                    variable_account_id = record.production_id.company_id.machine_run_cost_account_id
                    fixed_account_id = record.production_id.company_id.machine_run_fixed_cost_account_id
                id_created_header = self.env['account.move'].create({
                    'journal_id': record.production_id.company_id.manufacturing_journal_id.id,
                    'date': final_date,
                    'ref': desc_wo,
                    'company_id': record.workcenter_id.company_id.id,
                    'manufacture_order_id': record.production_id.id,
                })
                if amount_variable:
                    id_credit_item_variable = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id': id_created_header.id,
                        'account_id': variable_account_id.id,
                        'product_id': record.production_id.product_id.id,
                        'name': " ".join(("Direct Variable Costs", record.name)),
                        'quantity': record.qty_output_wo,
                        'product_uom_id': record.production_id.product_uom_id.id,
                        'credit': amount_variable,
                        'debit': 0.0,
                    })
                    id_debit_item_variable = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id': id_created_header.id,
                        'account_id': record.production_id.product_id.property_stock_production.valuation_account_id.id,
                        'analytic_distribution': analytic_distribution,
                        'product_id': record.production_id.product_id.id,
                        'name': " ".join(("Direct Variable Costs", record.name)),
                        'quantity': record.qty_output_wo,
                        'product_uom_id': record.production_id.product_uom_id.id,
                        'credit': 0.0,
                        'debit': amount_variable,
                    })
                if amount_fixed:
                    id_credit_item_fixed = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id': id_created_header.id,
                        'account_id': fixed_account_id.id,
                        'product_id': record.production_id.product_id.id,
                        'name': " ".join(("Direct Fixed Costs", record.name)),
                        'quantity': record.qty_output_wo,
                        'product_uom_id': record.production_id.product_uom_id.id,
                        'credit': amount_fixed,
                        'debit': 0.0,
                    })
                    id_debit_item_fixed = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id': id_created_header.id,
                        'account_id': record.production_id.product_id.property_stock_production.valuation_account_id.id,
                        'analytic_distribution': analytic_distribution,
                        'product_id': record.production_id.product_id.id,
                        'name': " ".join(("Direct Fixed Costs", record.name)),
                        'quantity': record.qty_output_wo,
                        'product_uom_id': record.production_id.product_uom_id.id,
                        'credit': 0.0,
                        'debit': amount_fixed,
                    })
                id_created_header.action_post()
