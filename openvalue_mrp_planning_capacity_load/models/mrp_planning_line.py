# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpPlanningLine(models.Model):
    _inherit = 'mrp.planning.line'

    required_hours = fields.Float(
        'Required Hours', compute='_compute_required_hours', store=True,
        help="Work-center hours required to manufacture the suggested quantity.")
    main_workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Main Work Center',
        compute='_compute_required_hours', store=True)
    available_hours = fields.Float(
        'Available Hours', compute='_compute_capacity_overloaded')
    capacity_overloaded = fields.Boolean(
        'Capacity Overload', compute='_compute_capacity_overloaded', store=True,
        help="The total planned hours on this line's work center exceed its "
             "available capacity over the horizon.")

    @api.depends('product_id', 'suggested_qty', 'supply_type')
    def _compute_required_hours(self):
        Bom = self.env['mrp.bom']
        for line in self:
            hours = 0.0
            workcenter = self.env['mrp.workcenter']
            if line.supply_type == 'manufacture' and line.suggested_qty:
                bom = Bom._bom_find(line.product_id)[line.product_id]
                if bom and bom.operation_ids:
                    hours = sum(
                        op.time_cycle_manual for op in bom.operation_ids
                    ) * line.suggested_qty / 60.0
                    workcenter = bom.operation_ids[0].workcenter_id
            line.required_hours = hours
            line.main_workcenter_id = workcenter

    @staticmethod
    def _wc_available_hours(workcenter, date_from, horizon_days):
        from datetime import datetime, time, timedelta
        start = datetime.combine(date_from, time.min)
        end = start + timedelta(days=horizon_days or 30)
        calendar = workcenter.resource_calendar_id
        if calendar:
            gross = calendar.get_work_hours_count(start, end)
        else:
            gross = (end - start).total_seconds() / 3600.0
        return gross * (workcenter.time_efficiency or 100.0) / 100.0

    @api.depends('required_hours', 'main_workcenter_id',
                 'run_id.line_ids.required_hours',
                 'run_id.line_ids.main_workcenter_id',
                 'run_id.capacity_horizon_days', 'run_id.date')
    def _compute_capacity_overloaded(self):
        for line in self:
            wc = line.main_workcenter_id
            if not wc or not line.run_id.date:
                line.available_hours = 0.0
                line.capacity_overloaded = False
                continue
            total_required = sum(line.run_id.line_ids.filtered(
                lambda l: l.main_workcenter_id == wc).mapped('required_hours'))
            available = line._wc_available_hours(
                wc, line.run_id.date, line.run_id.capacity_horizon_days)
            line.available_hours = available
            line.capacity_overloaded = total_required > available
