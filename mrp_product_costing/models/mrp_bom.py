# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    costs_planned_variances_analytic_account_id = fields.Many2one(
        'account.analytic.account', "Planned Variance Costs Analytic Account")
    costs_material_variances_analytic_account_id = fields.Many2one(
        'account.analytic.account', "Components Variance Costs Analytic Account")
    costs_direct_variances_analytic_account_id = fields.Many2one(
        'account.analytic.account', "Direct Variance Costs Analytic Account")
    # overheads
    costs_overhead_product_percentage = fields.Float('OVH Costs Product percentage', default=0.0)
    costs_overhead_components_percentage = fields.Float('OVH Costs Components percentage', default=0.0)
    overhead_analytic_account_id = fields.Many2one(
        'account.analytic.account', "OVH Costs Analytic Account")
