# -*- coding: utf-8 -*-

from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    PLANNING_MODE = [('F', 'Forward'), ('B', 'Backward')]

    planning_mode = fields.Selection(
        PLANNING_MODE, 'Planning Mode', default='F', required=True, copy=False)
    date_planned_start_pivot = fields.Datetime(
        'Planned Start Pivot Date', copy=False, default=fields.Datetime.now)
    date_planned_finished_pivot = fields.Datetime('Planned End Pivot Date', copy=False)
    date_planned_start_wo = fields.Datetime("Scheduled Start Date", readonly=True, copy=False)
    date_planned_finished_wo = fields.Datetime("Scheduled End Date", readonly=True, copy=False)
    date_actual_start_wo = fields.Datetime(
        'Start Date', copy=False, readonly=True, compute='_compute_actual_dates', store=True)
    date_actual_finished_wo = fields.Datetime(
        'End Date', copy=False, readonly=True, compute='_compute_actual_dates', store=True)
    is_scheduled = fields.Boolean(
        'Its Operations are Scheduled', compute='_compute_is_scheduled', store=True)

    # Time management ----------------------------------------------------------
    hours_uom = fields.Many2one('uom.uom', 'Hours', compute='_compute_hours_uom')
    std_setup_time = fields.Float('Total Setup Time', compute='_compute_standard_times', digits=(16, 2))
    std_teardown_time = fields.Float('Total Cleanup Time', compute='_compute_standard_times', digits=(16, 2))
    std_working_time = fields.Float('Total Working Time', compute='_compute_standard_times', digits=(16, 2))
    std_overall_time = fields.Float('Overall Time', compute='_compute_standard_times', digits=(16, 2))
    planned_duration_expected = fields.Float('Planned Times', copy=False, readonly=True, digits=(16, 2))
    unplanned_duration_expected = fields.Float('Unplanned Times', copy=False, readonly=True, digits=(16, 2))
    act_setup_time = fields.Float('Total Setup Time', compute='_compute_actual_times', digits=(16, 2))
    act_teardown_time = fields.Float('Total Cleanup Time', compute='_compute_actual_times', digits=(16, 2))
    act_working_time = fields.Float('Total Working Time', compute='_compute_actual_times', digits=(16, 2))
    act_overall_time = fields.Float('Overall Time', compute='_compute_actual_times', digits=(16, 2))
    qty_confirmed = fields.Float('Confirmed Qty', digits='Product Unit', copy=False, readonly=True)

    # --- Pivot date handling --------------------------------------------------
    @api.onchange('planning_mode', 'date_planned_start_pivot', 'product_id',
                  'company_id', 'picking_type_id', 'bom_id')
    def _onchange_forward_planning(self):
        for production in self:
            if production.planning_mode == 'F' and production.date_planned_start_pivot:
                production.date_planned_finished_pivot = production.get_planned_pivot_finished_date(
                    production.date_planned_start_pivot)

    @api.onchange('planning_mode', 'date_planned_finished_pivot', 'product_id',
                  'company_id', 'picking_type_id', 'bom_id')
    def _onchange_backward_planning(self):
        for production in self:
            if production.planning_mode == 'B' and production.date_planned_finished_pivot:
                production.date_planned_start_pivot = production.get_planned_pivot_start_date(
                    production.date_planned_finished_pivot)

    @api.constrains('date_planned_start_pivot', 'date_planned_finished_pivot')
    def _check_pivot_dates(self):
        for production in self:
            if (production.date_planned_start_pivot and production.date_planned_finished_pivot
                    and production.date_planned_start_pivot > production.date_planned_finished_pivot):
                raise ValidationError(_("The planned start pivot date must precede the end pivot date."))

    def _apply_pivot_dates(self):
        """Mirror the pivot dates onto the standard MO dates and align the
        related stock moves and pickings.  Called from confirm / plan, never
        from a constraint."""
        for production in self:
            if production.state in ('done', 'cancel'):
                continue
            if not production.date_planned_finished_pivot and production.date_planned_start_pivot:
                production.date_planned_finished_pivot = production.get_planned_pivot_finished_date(
                    production.date_planned_start_pivot)
            if production.date_planned_start_pivot:
                production.date_start = production.date_planned_start_pivot
            if production.date_planned_finished_pivot:
                production.date_finished = production.date_planned_finished_pivot
            production._align_stock_moves_dates()
            production._align_pickings_dates()

    def _get_security_lead(self):
        """Security lead time in days (per-BoM in Odoo 19)."""
        self.ensure_one()
        return self.bom_id.days_to_prepare_mo or 0

    def get_planned_pivot_finished_date(self, date_start):
        self.ensure_one()
        production = self
        if production.bom_id.type == 'subcontract':
            supplier_delay = production._get_subcontractor_delay()
            return date_start + timedelta(days=supplier_delay)
        produce_delay = int(production.bom_id.produce_delay or 0)
        security_lead = production._get_security_lead()
        calendar = production.picking_type_id.warehouse_id.calendar_id
        if calendar:
            anchor = calendar.plan_hours(0.0, date_start, compute_leaves=True)
            date_finished = calendar.plan_days(produce_delay + 1, anchor, compute_leaves=True)
            if security_lead > 0:
                date_finished = calendar.plan_days(security_lead + 1, date_finished, compute_leaves=True)
        else:
            date_finished = date_start + relativedelta(days=produce_delay + 1)
            if security_lead > 0:
                date_finished = date_finished + relativedelta(days=security_lead + 1)
        if date_finished == date_start:
            date_finished = date_start + relativedelta(hours=1)
        return date_finished

    def get_planned_pivot_start_date(self, date_finished):
        self.ensure_one()
        production = self
        if production.bom_id.type == 'subcontract':
            supplier_delay = production._get_subcontractor_delay()
            return date_finished - timedelta(days=supplier_delay)
        produce_delay = int(production.bom_id.produce_delay or 0)
        security_lead = production._get_security_lead()
        calendar = production.picking_type_id.warehouse_id.calendar_id
        if calendar:
            anchor = calendar.plan_hours(0.0, date_finished, compute_leaves=True)
            date_start = calendar.plan_days(-produce_delay - 1, anchor, compute_leaves=True)
            if security_lead > 0:
                date_start = calendar.plan_days(-security_lead - 1, date_start, compute_leaves=True)
        else:
            date_start = date_finished - relativedelta(days=produce_delay + 1)
            if security_lead > 0:
                date_start = date_start - relativedelta(days=security_lead + 1)
        if date_finished == date_start:
            date_start = date_finished - relativedelta(hours=1)
        return date_start

    def _get_subcontractor_delay(self):
        """Subcontractor lead time (days). Only reachable when the optional
        ``mrp_subcontracting`` module makes ``bom.type == 'subcontract'``
        available; inert otherwise."""
        self.ensure_one()
        subcontractor = self.procurement_group_id.partner_id
        sellers = (self.bom_id.product_id.seller_ids
                   | self.bom_id.product_tmpl_id.seller_ids)
        subs = sellers.filtered(lambda s: s.partner_id == subcontractor)
        return (subs[0].delay if subs else 0) or 1.0

    # --- Aggregated computes --------------------------------------------------
    @api.depends('workorder_ids.date_planned_start_wo', 'workorder_ids.state')
    def _compute_is_scheduled(self):
        for production in self:
            wos = production.workorder_ids
            # An MO is "scheduled" when every work order is either planned or
            # already done/cancelled. Using all() (not any() over only the
            # not-done WOs) keeps is_scheduled True once production completes —
            # otherwise button_mark_done's guard becomes unreachable for any MO
            # with work orders (all-done -> empty generator -> any() == False).
            production.is_scheduled = bool(wos) and all(
                wo.date_planned_start_wo or wo.state in ('done', 'cancel')
                for wo in wos)

    def _compute_hours_uom(self):
        uom = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)
        for production in self:
            production.hours_uom = uom.id if uom else False

    @api.depends('state', 'workorder_ids.state', 'workorder_ids.time_ids')
    def _compute_actual_dates(self):
        for production in self:
            start = finished = False
            done_wos = production.workorder_ids.filtered(lambda w: w.state == 'done')
            times = done_wos.time_ids
            if times:
                started = times.filtered('date_start')
                ended = times.filtered('date_end')
                if started:
                    start = started.sorted('date_start')[0].date_start
                if ended:
                    finished = ended.sorted('date_end')[-1].date_end
            production.date_actual_start_wo = start
            production.date_actual_finished_wo = finished

    @api.depends('workorder_ids.time_ids.overall_duration', 'workorder_ids.state')
    def _compute_actual_times(self):
        for production in self:
            setup = teardown = working = overall = 0.0
            for workorder in production.workorder_ids.filtered(lambda w: w.state == 'done'):
                for time in workorder.time_ids:
                    setup += time.setup_duration
                    working += time.working_duration
                    teardown += time.teardown_duration
                    overall += time.overall_duration
            production.act_setup_time = setup / 60.0
            production.act_teardown_time = teardown / 60.0
            production.act_working_time = working / 60.0
            production.act_overall_time = overall / 60.0

    @api.depends('bom_id', 'product_qty')
    def _compute_standard_times(self):
        for production in self:
            setup = teardown = working = 0.0
            bom_qty = production.bom_id.product_qty or 1.0
            for operation in production.bom_id.operation_ids:
                workcenter = operation.workcenter_id
                if not workcenter:
                    continue
                setup += workcenter.time_start
                teardown += workcenter.time_stop
                capacity = workcenter._sfc_capacity(production.product_id) or 1.0
                efficiency = workcenter.time_efficiency or 100.0
                cycle_number = float_round(
                    production.product_qty / capacity, precision_digits=0, rounding_method='UP')
                working += (cycle_number * operation.time_cycle * 100.0 / efficiency) / bom_qty
            production.std_setup_time = setup / 60.0
            production.std_teardown_time = teardown / 60.0
            production.std_working_time = working / 60.0
            production.std_overall_time = (setup + teardown + working) / 60.0

    def _align_durations(self):
        for production in self:
            planned = unplanned = 0.0
            for workorder in production.workorder_ids:
                if workorder.operation_id:
                    planned += workorder.duration_expected
                else:
                    unplanned += workorder.duration_expected
            production.planned_duration_expected = planned / 60.0
            production.unplanned_duration_expected = unplanned / 60.0

    # --- Move / picking alignment --------------------------------------------
    def _align_stock_moves_dates(self):
        for production in self:
            if production.date_planned_finished_pivot and production.date_planned_start_pivot:
                production.move_finished_ids.write({
                    'date': production.date_planned_finished_pivot,
                    'date_deadline': production.date_planned_finished_pivot,
                })
                production.move_raw_ids.write({
                    'date': production.date_planned_start_pivot,
                    'date_deadline': production.date_planned_start_pivot,
                })

    def _align_pickings_dates(self):
        for production in self:
            if not (production.date_planned_finished_pivot and production.date_planned_start_pivot):
                continue
            open_pickings = production.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            open_pickings.write({
                'scheduled_date': production.date_planned_start_pivot,
                'date_deadline': production.date_planned_start_pivot,
            })
            if production.picking_type_id.warehouse_id.manufacture_steps == 'pbm_sam':
                for picking in open_pickings.filtered(lambda p: p.location_dest_id == production.location_src_id):
                    picking.write({
                        'scheduled_date': production.date_planned_start_pivot,
                        'date_deadline': production.date_planned_start_pivot,
                    })
                for picking in open_pickings.filtered(lambda p: p.location_id == production.location_dest_id):
                    picking.write({
                        'scheduled_date': production.date_planned_finished_pivot,
                        'date_deadline': production.date_planned_finished_pivot,
                    })

    # --- Actions --------------------------------------------------------------
    def action_capacity_check(self):
        self.ensure_one()
        wizard = self.env['mrp.capacity.check'].create({'production_id': self.id})
        wizard._populate()
        return {
            'name': _('Capacity Check'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.capacity.check',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        res = super().action_confirm()
        for production in self:
            if production.bom_id.type == 'subcontract':
                production._confirm_subcontract_dates()
            production._align_durations()
            production.qty_confirmed = production.product_qty
            production._apply_pivot_dates()
        return res

    def _confirm_subcontract_dates(self):
        self.ensure_one()
        supplier_delay = self._get_subcontractor_delay()
        receipt_move = self.env['stock.move'].search(
            [('reference', '=', self.procurement_group_id.name)], limit=1)
        if receipt_move:
            self.date_planned_start_pivot = receipt_move.date - timedelta(days=supplier_delay)
            receipt_move.date_deadline = receipt_move.date
        delivery = self.env['stock.picking'].search([
            ('group_id', '=', self.procurement_group_id.id),
            ('state', 'not in', ('done', 'cancel')),
            ('picking_type_id.code', '=', 'outgoing'),
        ], limit=1)
        if delivery:
            delivery.scheduled_date = delivery.date_deadline

    # --- Scheduling -----------------------------------------------------------
    def schedule_workorders(self):
        for production in self:
            production.date_planned_start_wo = False
            production.date_planned_finished_wo = False
            if not production.workorder_ids:
                continue
            warehouse = production.picking_type_id.warehouse_id
            floating = self.env['mrp.floating.times']._get_for_warehouse(warehouse)
            warehouse_calendar = warehouse.calendar_id
            start_date = production.date_planned_start_pivot or fields.Datetime.now()
            if warehouse_calendar:
                if floating.mrp_release_time > 0.0:
                    start_date = warehouse_calendar.plan_hours(
                        floating.mrp_release_time, start_date, compute_leaves=True)
                if floating.mrp_ftbp_time > 0.0:
                    start_date = warehouse_calendar.plan_hours(
                        floating.mrp_ftbp_time, start_date, compute_leaves=True)
            production.date_planned_start_wo = start_date

            ordered = production.workorder_ids.sorted(key=lambda w: w.sfc_sequence)
            first = ordered[0]
            first.date_planned_start_wo = start_date
            calendar = first.workcenter_id.resource_calendar_id
            if calendar:
                first.date_planned_start_wo = calendar.plan_hours(
                    0.0, first.date_planned_start_wo, compute_leaves=True)
            first.forwards_scheduling()
            max_date_finished = first.date_planned_finished_wo
            current = first
            for workorder in ordered[1:]:
                if workorder.state in ('done', 'cancel'):
                    continue
                if current.sfc_sequence == workorder.sfc_sequence:
                    workorder.date_planned_start_wo = current.date_planned_start_wo
                else:
                    workorder.date_planned_start_wo = max_date_finished
                workorder.forwards_scheduling()
                max_date_finished = max(
                    workorder.date_planned_finished_wo, current.date_planned_finished_wo)
                current = workorder

            warehouse_calendar = warehouse.calendar_id
            if warehouse_calendar and floating.mrp_ftap_time > 0.0 and max_date_finished:
                max_date_finished = warehouse_calendar.plan_hours(
                    floating.mrp_ftap_time, max_date_finished, compute_leaves=True)
            production.date_planned_finished_wo = max_date_finished
            production.workorder_ids._rebuild_capacity_load()

    def button_plan(self):
        res = super().button_plan()
        for production in self:
            production.schedule_workorders()
            production._align_stock_moves_dates()
            production._align_pickings_dates()
        return res

    def button_unplan(self):
        res = super().button_unplan()
        for production in self:
            production.workorder_ids.write({
                'date_planned_start_wo': False,
                'date_planned_finished_wo': False,
            })
            self.env['mrp.workcenter.load'].search(
                [('workorder_id', 'in', production.workorder_ids.ids)]).unlink()
            production.date_planned_start_wo = False
            production.date_planned_finished_wo = False
        return res

    def action_cancel(self):
        for production in self:
            if any(wo.state == 'progress' for wo in production.workorder_ids):
                raise UserError(_('A work order is still running, please close it first.'))
            self.env['mrp.workcenter.load'].search(
                [('workorder_id', 'in', production.workorder_ids.ids)]).unlink()
        return super().action_cancel()

    def button_mark_done(self):
        for production in self:
            if production.workorder_ids:
                if not production.is_scheduled:
                    raise UserError(_('Work orders are not scheduled yet, please schedule them first.'))
                if any(wo.state not in ('done', 'cancel') for wo in production.workorder_ids):
                    raise UserError(_('Work orders are not processed yet, please close them first.'))
        return super().button_mark_done()
