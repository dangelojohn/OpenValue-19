# -*- coding: utf-8 -*-

from odoo import fields, models


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
