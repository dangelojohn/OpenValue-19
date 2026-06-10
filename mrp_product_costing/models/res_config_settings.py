# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    planned_variances_account_id = fields.Many2one(related="company_id.planned_variances_account_id", readonly=False)
    material_variances_account_id = fields.Many2one(related="company_id.material_variances_account_id", readonly=False)
    other_variances_account_id = fields.Many2one(related="company_id.other_variances_account_id", readonly=False)
    manufacturing_journal_id = fields.Many2one(related="company_id.manufacturing_journal_id", readonly=False)
    labour_cost_account_id = fields.Many2one(related="company_id.labour_cost_account_id", readonly=False)
    machine_run_cost_account_id = fields.Many2one(related="company_id.machine_run_cost_account_id", readonly=False)
    labour_fixed_cost_account_id = fields.Many2one(related="company_id.labour_fixed_cost_account_id", readonly=False)
    machine_run_fixed_cost_account_id = fields.Many2one(related="company_id.machine_run_fixed_cost_account_id", readonly=False)
