# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    # --- Shop Floor Control scheduling layer ----------------------------------
    # These planned dates are an independent SFC scheduling layer.  We do NOT
    # write the standard ``date_start`` / ``date_finished`` (which are coupled
    # to ``leave_id`` and managed by Odoo's own planner) to avoid creating
    # duplicate calendar leaves.
    date_planned_start_wo = fields.Datetime('SFC Scheduled Start', copy=False)
    date_planned_finished_wo = fields.Datetime('SFC Scheduled End', copy=False)
    date_actual_start_wo = fields.Datetime(
        'Actual Start Date', compute='_compute_dates_actual', store=True, copy=False)
    date_actual_finished_wo = fields.Datetime(
        'Actual End Date', compute='_compute_dates_actual', store=True, copy=False)

    qty_output_wo = fields.Float(
        'WO Quantity', digits='Product Unit', copy=False)
    qty_output_prev_wo = fields.Float(
        'Previous WO Quantity', digits='Product Unit', compute='_compute_prev_work_order')
    prev_work_order_id = fields.Many2one(
        'mrp.workorder', 'Previous Work Order', compute='_compute_prev_work_order')

    milestone = fields.Boolean(
        'Milestone', compute='_compute_milestone', store=True, readonly=False)
    sfc_sequence = fields.Integer(
        'SFC Sequence', compute='_compute_sfc_sequence', store=True, readonly=False,
        help="Sequence used by Shop Floor Control. Operations sharing the same "
             "SFC sequence run in parallel. Derived from the routing operation.")
    hours_uom = fields.Many2one('uom.uom', 'Hours', related='workcenter_id.hours_uom')
    wo_capacity_requirements = fields.Float(
        'WO Capacity Requirements', compute='_compute_wo_capacity_requirements', store=True)
    overall_duration = fields.Float(
        'Overall Duration', compute='_compute_overall_duration', store=True)

    # --- Computes -------------------------------------------------------------
    @api.depends('operation_id', 'operation_id.milestone')
    def _compute_milestone(self):
        for workorder in self:
            workorder.milestone = bool(workorder.operation_id.milestone)

    @api.depends('operation_id', 'operation_id.sequence')
    def _compute_sfc_sequence(self):
        for workorder in self:
            if workorder.operation_id:
                workorder.sfc_sequence = workorder.operation_id.sequence
            elif not workorder.sfc_sequence:
                workorder.sfc_sequence = workorder.sequence or 100

    @api.depends('time_ids.overall_duration')
    def _compute_overall_duration(self):
        for workorder in self:
            workorder.overall_duration = sum(workorder.time_ids.mapped('overall_duration'))

    @api.depends('duration_expected')
    def _compute_wo_capacity_requirements(self):
        for workorder in self:
            workorder.wo_capacity_requirements = workorder.duration_expected / 60.0

    @api.depends('state', 'sfc_sequence', 'production_id.workorder_ids.qty_output_wo')
    def _compute_prev_work_order(self):
        for workorder in self:
            prev = workorder.production_id.workorder_ids.filtered(
                lambda w: w.id != workorder.id and w.sfc_sequence < workorder.sfc_sequence)
            if prev:
                prev = prev.sorted(key=lambda w: w.sfc_sequence, reverse=True)[0]
                workorder.prev_work_order_id = prev
                workorder.qty_output_prev_wo = prev.qty_output_wo
            else:
                workorder.prev_work_order_id = False
                workorder.qty_output_prev_wo = workorder.production_id.product_qty

    @api.depends('time_ids', 'state')
    def _compute_dates_actual(self):
        for workorder in self:
            date_start = date_end = False
            if workorder.state == 'done' and workorder.time_ids:
                date_start = workorder.time_ids.sorted('date_start')[0].date_start
                ended = workorder.time_ids.filtered('date_end')
                if ended:
                    date_end = ended.sorted('date_end')[-1].date_end
            workorder.date_actual_start_wo = date_start
            workorder.date_actual_finished_wo = date_end

    # --- Constraints ----------------------------------------------------------
    @api.constrains('milestone', 'sfc_sequence')
    def _check_milestone(self):
        for workorder in self:
            siblings = workorder.production_id.workorder_ids.filtered(
                lambda w: w.id != workorder.id and w.sfc_sequence == workorder.sfc_sequence)
            if workorder.milestone and siblings:
                raise ValidationError(_(
                    "No parallel operation is allowed for a milestone work order."))
            if siblings.filtered('milestone'):
                raise ValidationError(_(
                    "No parallel operation is allowed for a milestone work order."))

    # --- Duration model -------------------------------------------------------
    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        self.ensure_one()
        if not self.workcenter_id:
            return self.duration_expected
        if not self.operation_id:
            working = (self.duration_expected - self.workcenter_id.time_start
                       - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / 100.0
            working = max(working, 0.0)
            return (self.workcenter_id.time_start + self.workcenter_id.time_stop
                    + working * ratio * 100.0 / self.workcenter_id.time_efficiency)
        qty_production = self.production_id.product_uom_id._compute_quantity(
            self.qty_production, self.production_id.product_id.uom_id)
        capacity = self.workcenter_id._sfc_capacity(self.production_id.product_id) or 1.0
        cycle_number = float_round(
            qty_production / capacity, precision_digits=0, rounding_method='UP')
        time_cycle = self.operation_id.time_cycle
        bom_qty = self.production_id.bom_id.product_qty or 1.0
        return (self.workcenter_id.time_start + self.workcenter_id.time_stop
                + cycle_number * time_cycle * (100.0 / self.workcenter_id.time_efficiency) / bom_qty)

    # --- Start / finish checks ------------------------------------------------
    def _get_maximum_quantity(self):
        self.ensure_one()
        max_qty = self.qty_output_prev_wo
        if self.milestone:
            closed = self.production_id.workorder_ids.filtered(
                lambda w: w.sfc_sequence < self.sfc_sequence and w.state == 'done')
            max_qty = min(closed.mapped('qty_output_wo')) if closed else self.qty_production
        if self.production_id.product_id.tracking == 'serial':
            max_qty = min(self.qty_output_prev_wo, 1)
        return max_qty

    def workorder_start_checks(self):
        for workorder in self:
            if not workorder.date_planned_start_wo:
                raise UserError(_('This work order has not been scheduled yet.'))
            if float_compare(workorder.qty_output_wo, workorder.qty_production,
                             precision_rounding=workorder.production_id.product_uom_id.rounding) > 0:
                raise UserError(_('It is not possible to produce more than the production order quantity.'))

    def workorder_finish_checks(self):
        for workorder in self:
            max_qty = workorder._get_maximum_quantity()
            if float_compare(workorder.qty_output_wo, max_qty,
                             precision_rounding=workorder.production_id.product_uom_id.rounding) > 0:
                raise UserError(_('It is not possible to produce more than %s.', max_qty))

    def button_start(self, raise_on_invalid_state=False):
        for workorder in self:
            if not workorder.qty_output_wo:
                workorder.qty_output_wo = (
                    workorder.qty_output_prev_wo if workorder.prev_work_order_id
                    else workorder.qty_production)
            missing = any(
                (float_compare(move.product_qty, move.forecast_availability,
                               precision_rounding=move.product_id.uom_id.rounding) > 0
                 or move.forecast_expected_date)
                for move in workorder.production_id.move_raw_ids.filtered(
                    lambda m: m.state not in ('done', 'cancel')))
            if missing and not workorder.workcenter_id.start_without_stock:
                raise UserError(_('It is not possible to start a work order without component availability.'))
            workorder.workorder_start_checks()
        return super().button_start(raise_on_invalid_state=raise_on_invalid_state)

    def button_finish(self):
        res = super().button_finish()
        for workorder in self:
            workorder.workorder_finish_checks()
            prev = workorder.production_id.workorder_ids.filtered(
                lambda w: w.sfc_sequence < workorder.sfc_sequence)
            if workorder.milestone:
                if any(w.state == 'progress' for w in prev):
                    raise UserError(_('A preceding work order is still in progress.'))
                to_cancel = prev.filtered(lambda w: w.state in ('blocked', 'ready'))
                to_cancel.write({'state': 'cancel'})
                self.env['mrp.workcenter.load'].search(
                    [('workorder_id', 'in', prev.ids)]).unlink()
            elif any(w.state not in ('done', 'cancel') for w in prev):
                raise UserError(_('Preceding work orders are not yet closed or cancelled.'))
            workorder.qty_producing = workorder.qty_output_wo
            self.env['mrp.workcenter.load'].search(
                [('workorder_id', '=', workorder.id)]).unlink()
        return res

    # --- Capacity load --------------------------------------------------------
    def _rebuild_capacity_load(self):
        """Recreate the daily capacity-load rows for the work order's SFC
        scheduling window."""
        Load = self.env['mrp.workcenter.load']
        for workorder in self:
            Load.search([('workorder_id', '=', workorder.id)]).unlink()
            start = workorder.date_planned_start_wo
            end = workorder.date_planned_finished_wo
            if not start or not end or not workorder.workcenter_id:
                continue
            calendar = workorder.workcenter_id.resource_calendar_id
            if not calendar:
                continue
            days = [start]
            cursor = start.date()
            for _i in range(max((end.date() - start.date()).days, 0)):
                cursor = cursor + timedelta(days=1)
                days.append(datetime.combine(cursor, datetime.min.time()))
            days.append(end)
            vals = []
            for i in range(len(days) - 1):
                hours = calendar.get_work_hours_count(days[i], days[i + 1])
                if hours > 0:
                    vals.append({
                        'workcenter_id': workorder.workcenter_id.id,
                        'workorder_id': workorder.id,
                        'product_id': workorder.production_id.product_id.id,
                        'product_qty': workorder.production_id.product_qty,
                        'product_uom_id': workorder.production_id.product_uom_id.id,
                        'date_planned': days[i],
                        'wo_capacity_requirements': hours * workorder.workcenter_id._sfc_capacity(workorder.production_id.product_id),
                    })
            if vals:
                Load.create(vals)

    # --- Scheduling helpers ---------------------------------------------------
    def forwards_scheduling(self):
        for workorder in self:
            calendar = workorder.workcenter_id.resource_calendar_id
            if calendar:
                workorder.date_planned_finished_wo = calendar.plan_hours(
                    workorder.duration_expected / 60.0, workorder.date_planned_start_wo, compute_leaves=True)
            else:
                workorder.date_planned_finished_wo = (
                    workorder.date_planned_start_wo + timedelta(minutes=workorder.duration_expected))

    def backwards_scheduling(self):
        for workorder in self:
            calendar = workorder.workcenter_id.resource_calendar_id
            if calendar:
                workorder.date_planned_start_wo = calendar.plan_hours(
                    -workorder.duration_expected / 60.0, workorder.date_planned_finished_wo, compute_leaves=True)
            else:
                workorder.date_planned_start_wo = (
                    workorder.date_planned_finished_wo - timedelta(minutes=workorder.duration_expected))

    def mid_point_scheduling_engine(self):
        """Re-plan the whole MO around this work order's start date, keeping
        parallel (same SFC sequence) and sequential operations consistent."""
        self.ensure_one()
        Workorder = self.env['mrp.workorder']
        workorder = self
        seq = workorder.sfc_sequence
        workorder.forwards_scheduling()
        min_date_start = workorder.date_planned_start_wo
        max_date_finished = workorder.date_planned_finished_wo

        # Parallel operations not yet started.
        for parallel in Workorder.search([
                ('production_id', '=', workorder.production_id.id),
                ('state', 'in', ('blocked', 'ready')),
                ('sfc_sequence', '=', seq), ('id', '!=', workorder.id)]):
            parallel.date_planned_start_wo = workorder.date_planned_start_wo
            parallel.forwards_scheduling()
            max_date_finished = max(parallel.date_planned_finished_wo, max_date_finished)

        # Parallel operations already in progress.
        for progress in Workorder.search([
                ('production_id', '=', workorder.production_id.id),
                ('state', '=', 'progress'),
                ('sfc_sequence', '=', seq), ('id', '!=', workorder.id)]):
            if progress.date_planned_finished_wo:
                max_date_finished = max(progress.date_planned_finished_wo, max_date_finished)

        # Preceding operations, scheduled backwards.
        prev_workorders = Workorder.search([
            ('production_id', '=', workorder.production_id.id),
            ('state', 'in', ('blocked', 'ready', 'progress')),
            ('sfc_sequence', '<', seq),
        ]).sorted(key=lambda w: (w.sfc_sequence, w.duration_expected), reverse=True)
        current = workorder
        for prev in prev_workorders:
            if prev.state == 'progress':
                if prev.date_planned_finished_wo and prev.date_planned_finished_wo > current.date_planned_start_wo:
                    raise UserError(_(
                        'Backward scheduling is not possible for the manufacturing order %s.',
                        workorder.production_id.name))
            elif current.sfc_sequence == prev.sfc_sequence:
                prev.date_planned_start_wo = current.date_planned_start_wo
                prev.forwards_scheduling()
            else:
                prev.date_planned_finished_wo = min_date_start
                prev.backwards_scheduling()
            min_date_start = min(prev.date_planned_start_wo or min_date_start, current.date_planned_start_wo)
            current = prev

        # Following operations, scheduled forwards.
        succ_workorders = Workorder.search([
            ('production_id', '=', workorder.production_id.id),
            ('state', 'in', ('blocked', 'ready')),
            ('sfc_sequence', '>', seq),
        ]).sorted(key=lambda w: w.sfc_sequence)
        current = workorder
        for succ in succ_workorders:
            if current.sfc_sequence == succ.sfc_sequence:
                succ.date_planned_start_wo = current.date_planned_start_wo
            else:
                succ.date_planned_start_wo = max_date_finished
            succ.forwards_scheduling()
            max_date_finished = max(succ.date_planned_finished_wo, current.date_planned_finished_wo)
            current = succ

        (workorder | prev_workorders | succ_workorders)._rebuild_capacity_load()
        workorder.production_id.date_planned_start_wo = min_date_start
        workorder.production_id.date_planned_finished_wo = max_date_finished
