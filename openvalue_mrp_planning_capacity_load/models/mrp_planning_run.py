# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpPlanningRun(models.Model):
    _inherit = 'mrp.planning.run'

    capacity_horizon_days = fields.Integer(
        'Capacity Horizon (days)', default=30,
        help="Window over which each work center's available capacity is "
             "assessed for the overload check.")
    overloaded_workcenter_count = fields.Integer(
        'Overloaded Work Centers', compute='_compute_overloaded_workcenter_count')

    def _compute_overloaded_workcenter_count(self):
        for run in self:
            run.overloaded_workcenter_count = len(
                run.line_ids.filtered('capacity_overloaded').main_workcenter_id)
