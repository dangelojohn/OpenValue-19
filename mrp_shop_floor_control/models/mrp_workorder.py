# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import float_compare, float_is_zero, float_round


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    _order = 'production_id, sequence, duration_expected, id'

    # Odoo Standard
    qty_production = fields.Float('Manufacturing Order Qty')
    # SFC
    date_actual_start_wo = fields.Datetime('Actual Start Date', compute='_compute_dates_actual', store=True, copy=False)
    date_actual_finished_wo = fields.Datetime('Actual End Date', compute='_compute_dates_actual', store=True, copy=False)
    date_planned_start_wo = fields.Datetime('Scheduled Start Date', readonly=True, states={'waiting': [('readonly', False)],'ready': [('readonly', False)],'pending': [('readonly', False)]}, copy=False)
    date_planned_finished_wo = fields.Datetime('Scheduled End Date', readonly=True, states={'waiting': [('readonly', False)],'ready': [('readonly', False)],'pending': [('readonly', False)]}, copy=False)
    qty_output_wo = fields.Float('WO Quantity', digits='Product Unit of Measure', copy=False, readonly=True)
    qty_output_prev_wo = fields.Float('Previous WO Quantity', digits='Product Unit of Measure', compute="_compute_prev_work_order")
    prev_work_order_id = fields.Many2one('mrp.workorder', 'Previous Work Order', compute="_compute_prev_work_order")
    milestone = fields.Boolean('Milestone', compute='_get_milestone',  store=True, readonly=True, states={'waiting': [('readonly', False)],'ready': [('readonly', False)],'pending': [('readonly', False)]}, copy=True)
    sequence = fields.Integer('Sequence', compute='_get_sequence', store=True, readonly=True, states={'waiting': [('readonly', False)],'ready': [('readonly', False)],'pending': [('readonly', False)]}, copy=True)
    hours_uom = fields.Many2one('uom.uom', 'Hours', related='workcenter_id.hours_uom')
    wo_capacity_requirements = fields.Float('WO Capacity Requirements', compute='_wo_capacity_requirement', store=True)
    overall_duration = fields.Float('Overall Duration', compute='_compute_overall_duration', store=True)


    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        self.ensure_one()
        if not self.workcenter_id:
            return self.duration_expected
        if not self.operation_id:
            duration_expected_working = (self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / 100.0
            if duration_expected_working < 0:
                duration_expected_working = 0
            return self.workcenter_id.time_start + self.workcenter_id.time_stop + duration_expected_working * ratio * 100.0 / self.workcenter_id.time_efficiency
        qty_production = self.production_id.product_uom_id._compute_quantity(self.qty_production, self.production_id.product_id.uom_id)
        cycle_number = float_round(qty_production / self.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
        #if alternative_workcenter:
        #    duration_expected_working = (self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / (100.0 * cycle_number)
        #    if duration_expected_working < 0:
        #        duration_expected_working = 0
        #    alternative_wc_cycle_nb = float_round(qty_production / alternative_workcenter.capacity, precision_digits=0, rounding_method='UP')
        #    return alternative_workcenter.time_start + alternative_workcenter.time_stop + alternative_wc_cycle_nb * duration_expected_working * 100.0 / alternative_workcenter.time_efficiency
        time_cycle = self.operation_id.time_cycle
        return self.workcenter_id.time_start + self.workcenter_id.time_stop + cycle_number * time_cycle * (100.0 / self.workcenter_id.time_efficiency) / self.production_id.bom_id.product_qty

    @api.depends('operation_id')
    def _get_milestone(self):
        for workorder in self:
            if workorder.operation_id and workorder.operation_id.milestone:
                workorder.milestone = True

    @api.depends('operation_id')
    def _get_sequence(self):
        for workorder in self:
            if workorder.operation_id and workorder.operation_id.sequence:
                workorder.sequence = workorder.operation_id.sequence

    @api.depends('time_ids.overall_duration')
    def _compute_overall_duration(self):
        for workorder in self:
            workorder.overall_duration = sum(workorder.time_ids.mapped('overall_duration'))

    @api.depends('duration_expected')
    def _wo_capacity_requirement(self):
        for workorder in self:
            workorder.wo_capacity_requirements = (workorder.duration_expected) / 60

    @api.depends('state')
    def _compute_prev_work_order(self):
        for workorder in self:
            prev_workorders = self.search([
                ('production_id', '=', workorder.production_id.id),
                ('sequence', '<', workorder.sequence),
            ])
            if prev_workorders:
                prev_workorders_sorted = prev_workorders.sorted(key=lambda r: r.sequence, reverse=True)
                workorder.prev_work_order_id = prev_workorders_sorted[0]
                workorder.qty_output_prev_wo = workorder.prev_work_order_id.qty_output_wo
            else:
                workorder.prev_work_order_id = False
                workorder.qty_output_prev_wo = workorder.production_id.product_qty

    @api.constrains('milestone','sequence')
    def ckeck_milestone(self):
        for workorder in self:
            other_workorders = self.search([
                ('production_id', '=', workorder.production_id.id),
                ('id', '!=', workorder.id)])
            if workorder.milestone:
                milestone_sequence = workorder.sequence
                if any(other_workorder.sequence == milestone_sequence for other_workorder in other_workorders):
                    raise UserError(_('no parallel operation is allowed for milestone'))
            else:
                workorder_sequence = workorder.sequence
                if any(other_workorder.sequence == workorder_sequence and other_workorder.milestone for other_workorder in other_workorders):
                    raise UserError(_('no parallel operation is allowed for milestone'))

    def button_start(self):
        for workorder in self:
            if workorder.qty_output_wo == 0.0:
                if not workorder.prev_work_order_id:
                    workorder.qty_output_wo = workorder.qty_production
                else:
                    workorder.qty_output_wo = workorder.qty_output_prev_wo
            if any((float_compare(move.product_qty, move.forecast_availability, precision_rounding=move.product_id.uom_id.rounding) > 0 or move.forecast_expected_date) for move in workorder.production_id.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))) and not workorder.workcenter_id.start_without_stock:
                raise UserError(_('It is not possible to start workorder without components availability'))
            workorder.workorder_start_checks()
        return super().button_start()

    def _get_maximum_quantity(self):
        max_qty = 0.0
        for workorder in self:
            max_qty = workorder.qty_output_prev_wo
            if workorder.milestone:
                prev_workorders_closed = workorder.production_id.workorder_ids.filtered(lambda x: (x.sequence < workorder.sequence and x.state == 'done'))
                if prev_workorders_closed:
                    max_qty = min(prev_workorders_closed.mapped('qty_output_wo'))
                else:
                    max_qty = workorder.qty_production
            if workorder.production_id.product_id.tracking == 'serial':
                max_qty = min(workorder.qty_output_prev_wo, 1)
        return max_qty

    def workorder_start_checks(self):
        for workorder in self:
            if not workorder.date_planned_start_wo:
                raise UserError(_('Manufacturing Order not scheduled yet'))
            if workorder.qty_output_wo > workorder.qty_production:
                raise UserError( _('It is not possible to produce more than production order quantity'))

    def workorder_finish_checks(self):
        for workorder in self:
            max_qty_output_wo = workorder._get_maximum_quantity()
            if workorder.qty_output_wo > max_qty_output_wo:
                raise UserError(_('It is not possible to produce more than %s') % max_qty_output_wo)

    @api.depends('time_ids','state')
    def _compute_dates_actual(self):
        date_start = False
        date_end = False
        for workorder in self:
            if workorder.state == 'done' and workorder.time_ids:
                date_start =  workorder.time_ids.sorted('date_start')[0].date_start
                date_end = workorder.time_ids.sorted('date_end')[-1].date_end
            workorder.date_actual_start_wo = date_start
            workorder.date_actual_finished_wo = date_end

    ## close workload
    def button_finish(self):
        super().button_finish()
        for workorder in self:
            workorder.workorder_finish_checks()
            workorders = workorder.production_id.workorder_ids
            prev_workorders = [x for x in workorders if x.sequence < workorder.sequence]
            if workorder.milestone:
                if any(prev_workorder.state == 'progress' for prev_workorder in prev_workorders):
                    raise UserError(_('previous workorder in progress'))
                for prev_workorder in prev_workorders:
                    if prev_workorder.state in ('ready','pending','waiting'):
                        prev_workorder.state = 'cancel'
                    wo_capacity_ids = self.env['mrp.workcenter.capacity'].search([('workorder_id', '=', prev_workorder.id)])
                    if wo_capacity_ids:
                        wo_capacity_ids.unlink()
            else:
                if any(prev_workorder.state not in ('done', 'cancel') for prev_workorder in prev_workorders):
                    raise UserError(_('previous workorders not yet closed or cancelled'))
            workorder.qty_producing = workorder.qty_output_wo
            wo_capacity_ids = self.env['mrp.workcenter.capacity'].search([('workorder_id', '=', workorder.id)])
            wo_capacity_ids.unlink()

    def _get_capacity_load(self, start_date, end_date):
        sdate =  start_date.date()
        edate = end_date.date()
        delta = edate - sdate
        list_days = []
        nro_hours = 0.0
        list_days.append(start_date)
        for i in range(delta.days):
            day = sdate + timedelta(days=i+1)
            day = datetime.combine(day, datetime.min.time())
            list_days.append(day)
        list_days.append(end_date)
        for i in range(len(list_days) - 1):
            for workorder in self:
                nro_hours = workorder.workcenter_id.resource_calendar_id.get_work_duration_data(list_days[i], list_days[i+1])['hours']
                if  nro_hours > 0:
                    id_created= self.env['mrp.workcenter.capacity'].create({
                        'workcenter_id': workorder.workcenter_id.id,
                        'workorder_id': workorder.id,
                        'product_id': workorder.production_id.product_id.id,
                        'product_qty': workorder.production_id.product_qty,
                        'product_uom_id': workorder.production_id.product_uom_id.id,
                        'date_planned': list_days[i],
                        'wo_capacity_requirements': nro_hours * workorder.workcenter_id.capacity,
                    })

    ## create/change workload
    @api.constrains('date_planned_start_wo', 'date_planned_finished_wo')
    def _change_scheduled_dates(self):
        for workorder in self:
            date_planned_start = workorder.date_planned_start_wo
            date_planned_finish = workorder.date_planned_finished_wo
            if date_planned_start and date_planned_finish:
                wo_capacity_ids = self.env['mrp.workcenter.capacity'].search([('workorder_id', '=', workorder.id)])
                wo_capacity_ids.unlink()
                workorder._get_capacity_load(date_planned_start, date_planned_finish)
                if date_planned_finish and date_planned_start and date_planned_finish > date_planned_start:
                    if date_planned_start and workorder.date_planned_finished and date_planned_start > workorder.date_planned_finished:
                        workorder.date_planned_finished = date_planned_finish
                        workorder.date_planned_start = date_planned_start
                    else:
                        workorder.date_planned_start = date_planned_start
                        workorder.date_planned_finished = date_planned_finish

    def backwards_scheduling(self):
        for workorder in self:
            time_delta = workorder.duration_expected
            workorder.date_planned_start_wo = workorder.date_planned_finished_wo - timedelta(minutes=time_delta)
            if workorder.workcenter_id.resource_calendar_id:
                calendar = workorder.workcenter_id.resource_calendar_id
                duration_expected = - workorder.duration_expected / 60
                workorder.date_planned_start_wo = calendar.plan_hours(duration_expected, workorder.date_planned_finished_wo, True)

    def forwards_scheduling(self):
        for workorder in self:
            time_delta = workorder.duration_expected
            workorder.date_planned_finished_wo = workorder.date_planned_start_wo + timedelta(minutes=time_delta)
            if workorder.workcenter_id.resource_calendar_id:
                calendar = workorder.workcenter_id.resource_calendar_id
                duration_expected = workorder.duration_expected / 60
                workorder.date_planned_finished_wo = calendar.plan_hours(duration_expected, workorder.date_planned_start_wo, True)