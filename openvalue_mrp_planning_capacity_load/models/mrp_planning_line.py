# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpPlanningLine(models.Model):
    _inherit = 'mrp.planning.line'

    required_hours = fields.Float(
        'Required Hours', compute='_compute_required_hours', store=True,
        help="Work-center hours required to manufacture the suggested quantity.")

    @api.depends('product_id', 'suggested_qty', 'supply_type')
    def _compute_required_hours(self):
        Bom = self.env['mrp.bom']
        for line in self:
            hours = 0.0
            if line.supply_type == 'manufacture' and line.suggested_qty:
                bom = Bom._bom_find(line.product_id)[line.product_id]
                if bom:
                    hours = sum(
                        op.time_cycle_manual for op in bom.operation_ids
                    ) * line.suggested_qty / 60.0
            line.required_hours = hours
