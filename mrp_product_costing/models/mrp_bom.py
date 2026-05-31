# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_round


class MrpBom(models.Model):
    _inherit = 'mrp.bom'


    costs_planned_variances_analytic_account_id = fields.Many2one('account.analytic.account', "Planned Variance Costs Analytic Account")
    costs_material_variances_analytic_account_id = fields.Many2one('account.analytic.account', "Components Variance Costs Analytic Account")
    costs_direct_variances_analytic_account_id = fields.Many2one('account.analytic.account', "Direct Variance Costs Analytic Account")
    # overheads
    costs_overhead_product_percentage = fields.Float('OVH Costs Product percentage', default=0.0)
    costs_overhead_components_percentage = fields.Float('OVH Costs Components percentage', default=0.0)
    overhead_analytic_account_id = fields.Many2one('account.analytic.account', "OVH Costs Analytic Account")


#class ReportBomStructure(models.AbstractModel):
#    _inherit = 'report.mrp.report_bom_structure'

#    def _get_operation_line(self, product, bom, qty, level):
#        operations = []
#        costfixed = costvar = total = 0.0
#        for operation in bom.operation_ids:
#            if operation._skip_operation_line(product):
#                continue
#            operation_cycle = float_round(qty / operation.workcenter_id.capacity, precision_rounding=1, rounding_method='UP')
#            duration_expected = operation_cycle * operation.time_cycle + operation.workcenter_id.time_stop + operation.workcenter_id.time_start
#            #total = ((duration_expected / 60.0) * operation.workcenter_id.costs_hour)
#            costvar = (operation_cycle * operation.time_cycle) * operation.workcenter_id.costs_hour / 60
#            costfixed  = ((operation.workcenter_id.time_stop + operation.workcenter_id.time_start) / qty)* operation.workcenter_id.costs_hour_fixed / 60
#            total = costvar + costfixed
#            operations.append({
#                'level': level or 0,
#                'operation': operation,
#                'name': operation.name + ' - ' + operation.workcenter_id.name,
#                'duration_expected': duration_expected,
#                'total': self.env.company.currency_id.round(total),
#            })
#        return operations
