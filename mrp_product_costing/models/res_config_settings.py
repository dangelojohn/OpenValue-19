# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    planned_variances_account_id = fields.Many2one('account.account', "Planned Variance Cost Account")
    material_variances_account_id = fields.Many2one('account.account', "Components Variance Cost Account")
    other_variances_account_id = fields.Many2one('account.account', "Direct Variance Cost Account")
    manufacturing_journal_id = fields.Many2one('account.journal', "Manufacturing Journal")
    labour_cost_account_id = fields.Many2one('account.account', "Labour Variable Cost Account")
    machine_run_cost_account_id = fields.Many2one('account.account', "Machine Run Variable Cost Account")
    labour_fixed_cost_account_id = fields.Many2one('account.account', "Labour Fixed Cost Account")
    machine_run_fixed_cost_account_id = fields.Many2one('account.account', "Machine Run Fixed Cost Account")


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

