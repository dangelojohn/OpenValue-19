# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    PLANNING_MODE = [
        ('F', 'Forward'),
        ('B', 'Backward'),
    ]
    # Odoo Standard
    lot_producing_id = fields.Many2one(states={'done': [('readonly', True)]})
    user_id = fields.Many2one(states={'done': [('readonly', True)]})
    # SFC
    planning_mode = fields.Selection(PLANNING_MODE, 'Planning Mode', default="F", required=True, readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]}, copy=False)
    date_planned_start_pivot = fields.Datetime('Planned Start Pivot Date', readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]}, default=lambda self: fields.datetime.now())
    date_planned_finished_pivot = fields.Datetime('Planned End Pivot Date', readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]}, compute='_compute_planned_pivot_finished_date', store=True)
    date_planned_start_wo = fields.Datetime("Scheduled Start Date", readonly=True, copy=False)
    date_planned_finished_wo = fields.Datetime("Scheduled End Date", readonly=True, copy=False)
    date_actual_start_wo = fields.Datetime('Start Date', copy=False, readonly=True, compute="get_actual_dates", store=True)
    date_actual_finished_wo = fields.Datetime('End Date', copy=False, readonly=True, compute="get_actual_dates", store=True)
    origin = fields.Char(readonly=True, states={'draft': [('readonly', False)]})
    is_scheduled = fields.Boolean('Its Operations are Scheduled', compute='_compute_is_scheduled', store=True)
    # Time Management
    hours_uom = fields.Many2one('uom.uom', 'Hours', compute="_get_uom_hours")
    std_setup_time = fields.Float('Total Setup Time', compute='_get_standard_times', digits=(16, 2))
    std_teardown_time = fields.Float('Total Cleanup Time', compute='_get_standard_times', digits=(16, 2))
    std_working_time = fields.Float('Total Working Time', compute='_get_standard_times', digits=(16, 2))
    std_overall_time = fields.Float('Overall Time', compute='_get_standard_times', digits=(16, 2))
    planned_duration_expected = fields.Float('Planned Times', copy=False, readonly=True, digits=(16, 2))
    unplanned_duration_expected = fields.Float('Unplanned Times', copy=False, readonly=True, digits=(16, 2))
    act_setup_time = fields.Float('Total Setup Time', compute='_get_actual_times', digits=(16, 2))
    act_teardown_time = fields.Float('Total Cleanup Time', compute='_get_actual_times', digits=(16, 2))
    act_working_time = fields.Float('Total Working Time', compute='_get_actual_times', digits=(16, 2))
    act_overall_time = fields.Float('Overall Time', compute='_get_actual_times', digits=(16, 2))
    qty_confirmed = fields.Float('Confirmed Qty', digits='Product Unit of Measure', copy=False, readonly=True)


    @api.onchange('planning_mode', 'date_planned_start_pivot', 'product_id', 'company_id', 'picking_type_id', 'bom_id')
    def onchange_planning_mode_forward(self):
        for production in self:
            if production.planning_mode == 'F' and production.date_planned_start_pivot:
                production.date_planned_finished_pivot = production.get_planned_pivot_finished_date(production.date_planned_start_pivot)

    @api.onchange('planning_mode', 'date_planned_finished_pivot', 'product_id', 'company_id', 'picking_type_id', 'bom_id')
    def onchange_planning_mode_backward(self):
        for production in self:
            if production.planning_mode == 'B' and production.date_planned_finished_pivot:
                production.date_planned_start_pivot = production.get_planned_pivot_start_date(production.date_planned_finished_pivot)

    @api.depends('date_planned_start_pivot', 'product_id', 'company_id', 'picking_type_id', 'bom_id.type', 'bom_id', 'planning_mode')
    def _compute_planned_pivot_finished_date(self):
        for production in self:
            if production.date_planned_start_pivot and production.planning_mode == 'F':
                production.date_planned_finished_pivot = production.get_planned_pivot_finished_date(production.date_planned_start_pivot)
        return True

    @api.constrains('date_planned_start_pivot', 'date_planned_finished_pivot')
    def check_dates(self):
        for production in self:
            if production.date_planned_finished_pivot and production.date_planned_start_pivot and production.date_planned_start_pivot > production.date_planned_finished_pivot:
                raise UserError(_("Please check planned pivot dates."))
            if production.state not in ('done', 'cancel'):
                production.date_planned_start = production.date_planned_start_pivot
                production.date_planned_finished = production.date_planned_finished_pivot

    def get_planned_pivot_finished_date(self, date_start):
        for production in self:
            if production.bom_id.type == 'subcontract':
                subcontractor = production.procurement_group_id.partner_id
                subs = production.bom_id.product_id.seller_ids.filtered(lambda sub: sub.name == subcontractor) or production.bom_id.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractor)
                if subs:
                    supplier_delay = subs[0].delay or 1.0
                else:
                    supplier_delay = 1.0
                date_finished = date_start + timedelta(days=supplier_delay)
            else:
                date_finished = date_start + relativedelta(days=production.product_id.produce_delay + 1)
                if production.company_id.manufacturing_lead > 0:
                    date_finished = date_finished + relativedelta(days=production.company_id.manufacturing_lead + 1)
                if production.picking_type_id.warehouse_id.calendar_id:
                    calendar = production.picking_type_id.warehouse_id.calendar_id
                    date_start = calendar.plan_hours(0.0, date_start, True)
                    date_finished = calendar.plan_days(int(production.product_id.produce_delay) + 1, date_start, True)
                    if production.company_id.manufacturing_lead > 0:
                        date_finished = calendar.plan_days(int(production.company_id.manufacturing_lead)  + 1, date_finished, True)
                if date_finished == date_start:
                    date_finished = date_start + relativedelta(hours=1)
        return date_finished

    def get_planned_pivot_start_date(self, date_finished):
        for production in self:
            if production.bom_id.type == 'subcontract':
                subcontractor = production.procurement_group_id.partner_id
                subs = production.bom_id.product_id.seller_ids.filtered(lambda sub: sub.name == subcontractor) or production.bom_id.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractor)
                if subs:
                    supplier_delay = subs[0].delay or 1.0
                else:
                    supplier_delay = 1.0
                date_start =  date_finished - timedelta(days=supplier_delay)
            else:
                date_start = date_finished - relativedelta(days=production.product_id.produce_delay + 1)
                if production.company_id.manufacturing_lead > 0:
                    date_start = date_start - relativedelta(days=production.company_id.manufacturing_lead + 1)
                if production.picking_type_id.warehouse_id.calendar_id:
                    calendar = production.picking_type_id.warehouse_id.calendar_id
                    date_finished = calendar.plan_hours(0.0, date_finished, True)
                    date_start = calendar.plan_days(-int(production.product_id.produce_delay) - 1, date_finished, True)
                    if production.company_id.manufacturing_lead > 0:
                        date_start = calendar.plan_days(-int(production.company_id.manufacturing_lead) - 1, date_start, True)
                if date_finished == date_start:
                    date_start =  date_finished - relativedelta(hours=1)
        return date_start

    def action_capacity_check(self):
        return {
            'name': _('Capacity Check'),
            'view_mode': 'form',
            'res_model': 'mrp.capacity.check',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_confirm(self):
        receipt_move = delivery_picking = False
        res = super().action_confirm()
        for production in self:
            if production.bom_id.type == 'subcontract':
                subcontractor = production.procurement_group_id.partner_id
                subs = production.bom_id.product_id.seller_ids.filtered(lambda sub: sub.name == subcontractor) or production.bom_id.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractor)
                if subs:
                    supplier_delay = subs[0].delay or 1.0
                else:
                    supplier_delay = 1.0
                receipt_move = self.env['stock.move'].search([('reference', '=', production.procurement_group_id.name)], limit=1)
                if receipt_move:
                    date_finished = receipt_move.date
                    date_start = date_finished - timedelta(days=supplier_delay)
                    production.date_planned_start_pivot = date_start
                    receipt_move.date_deadline = receipt_move.date
                delivery_picking = self.env['stock.picking'].search([
                    ('group_id', '=', production.procurement_group_id.name),
                    ('state', 'not in', ('done', 'cancel')),
                    ('picking_type_id.code', '=', 'outgoing'),
                    ], limit=1)
                if delivery_picking:
                    delivery_picking.scheduled_date = delivery_picking.date_deadline
            production._align_durations()
            production.qty_confirmed = production.product_qty
            production._align_pickings_dates()
        return res

    def _align_durations(self):
        planned_duration_expected = unplanned_duration_expected = 0.0
        for production in self:
            for workorder in production.workorder_ids.filtered(lambda r: r.operation_id.id != False):
                planned_duration_expected += workorder.duration_expected
            production.planned_duration_expected = planned_duration_expected / 60
            for workorder in production.workorder_ids.filtered(lambda r: r.operation_id.id == False):
                unplanned_duration_expected += workorder.duration_expected
            production.unplanned_duration_expected = unplanned_duration_expected /60

    @api.depends("workorder_ids.date_planned_start_wo")
    def _compute_is_scheduled(self):
        for production in self:
            production.is_scheduled = False
            if production.workorder_ids:
                production.is_scheduled = any(workorder.date_planned_start_wo for workorder in production.workorder_ids if workorder.state not in ('done', 'cancel'))

    # scheduling
    def schedule_workorders(self):
        max_date_finished = False
        start_date = False
        for production in self:
            production.date_planned_start_wo = False
            production.date_planned_finished_wo = False
            floating_times_id = self.env['mrp.floating.times'].search([('warehouse_id', '=', production.picking_type_id.warehouse_id.id)])
            if not floating_times_id:
                raise UserError(_('Floating Times record has not been created yet for the warehouse: %s')% production.picking_type_id.warehouse_id.name)
            warehouse_calendar = production.picking_type_id.warehouse_id.calendar_id
            start_date = production.date_planned_start_pivot or fields.Datetime.now()
            # Release production
            release_time = floating_times_id.mrp_release_time
            if release_time > 0.0 and warehouse_calendar:
                start_date = warehouse_calendar.plan_hours(release_time, start_date, True)
            # before production
            before_production_time = floating_times_id.mrp_ftbp_time
            if before_production_time > 0.0 and warehouse_calendar:
                start_date = warehouse_calendar.plan_hours(before_production_time, start_date, True)
            production.date_planned_start_wo = start_date
            # workorders scheduling
            first_workorder = production.workorder_ids[0]
            sequence_wo = first_workorder.sequence
            first_workorder.date_planned_start_wo = start_date
            calendar = first_workorder.workcenter_id.resource_calendar_id
            if calendar:
                first_workorder.date_planned_start_wo = calendar.plan_hours(0.0, first_workorder.date_planned_start_wo, True)
            first_workorder.forwards_scheduling()
            max_date_finished = first_workorder.date_planned_finished_wo
            succ_workorders = self.env['mrp.workorder'].search([
                ('production_id', '=', first_workorder.production_id.id),
                ('state', 'in', ('ready','pending', 'waiting')),
                ('sequence', '>=', sequence_wo),
                ('id', '!=', first_workorder.id),
                ]).sorted(key=lambda r: r.sequence)
            if succ_workorders:
                current_workorder = first_workorder
                for succ_workorder in succ_workorders:
                    # workorder in parallelo
                    if current_workorder.sequence == succ_workorder.sequence:
                        succ_workorder.date_planned_start_wo = current_workorder.date_planned_start_wo
                        succ_workorder.forwards_scheduling()
                    # workorder in sequenza
                    else:
                        succ_workorder.date_planned_start_wo = max_date_finished
                        succ_workorder.forwards_scheduling()
                    max_date_finished = max(succ_workorder.date_planned_finished_wo, current_workorder.date_planned_finished_wo)
                    current_workorder = succ_workorder
            # after production
            after_production_time = floating_times_id.mrp_ftap_time
            if after_production_time > 0.0 and warehouse_calendar:
                max_date_finished = warehouse_calendar.plan_hours(after_production_time, max_date_finished, True)
            production.date_planned_finished_wo = max_date_finished

    def button_plan(self):
        res = super().button_plan()
        for production in self:
            production.schedule_workorders()
            production._align_stock_moves_dates()
            production._align_pickings_dates()
        return res

    # delete capacity load
    def button_unplan(self):
        res = super().button_unplan()
        for production in self:
            for workorder in production.workorder_ids:
                workorder.date_planned_start_wo = False
                workorder.date_planned_finished_wo = False
            wo_capacity_ids = self.env['mrp.workcenter.capacity'].search([('workorder_id', 'in', production.workorder_ids.ids)])
            wo_capacity_ids.unlink()
            production.date_planned_start_wo = False
            production.date_planned_finished_wo = False
        return res

    @api.depends('state')
    def get_actual_dates(self):
        for production in self:
            if production.workorder_ids:
                if production.state == "done" and production.workorder_ids:
                    workorders = self.env['mrp.workorder'].search([('production_id', '=', production.id),('state', '=', 'done')])
                    time_records = self.env['mrp.workcenter.productivity'].search([('workorder_id', 'in', workorders.ids)])
                    if time_records:
                        production.date_actual_start_wo = time_records.sorted('date_start')[0].date_start
                        production.date_actual_finished_wo = time_records.sorted('date_end')[-1].date_end
            else:
                if production.state == "confirmed":
                    production.write({'date_actual_start_wo': fields.Datetime.now()})
                if production.state == "done":
                    production.write({'date_actual_finished_wo': fields.Datetime.now()})

    # delete capacity load
    def action_cancel(self):
        for production in self:
            if production.workorder_ids:
                wo_capacity_ids = self.env['mrp.workcenter.capacity'].search([('workorder_id', 'in', production.workorder_ids.ids)])
                wo_capacity_ids.unlink()
                if any(workorder.state == 'progress' for workorder in production.workorder_ids):
                    raise UserError(_('workorder still running, please close it'))
        return super().action_cancel()

    def button_mark_done(self):
        res = super().button_mark_done()
        for production in self:
            if production.workorder_ids:
                if not production.is_scheduled:
                    raise UserError(_('workorders not yet scheduled, please schedule them before'))
                if any(workorder.state not in ('done', 'cancel') for workorder in production.workorder_ids):
                    raise UserError(_('workorders not yet processed, please close them before'))
        return res

    @api.constrains('date_planned_start_pivot', 'date_planned_finished_pivot', 'state')
    def _align_picking_moves_dates(self):
        for production in self:
            production._align_stock_moves_dates()
            production._align_pickings_dates()

    def _align_stock_moves_dates(self):
        for production in self:
            if production.date_planned_finished_pivot and production.date_planned_start_pivot:
                production.move_finished_ids.write({'date': production.date_planned_finished_pivot, 'date_deadline': production.date_planned_finished_pivot})
                production.move_raw_ids.write({'date': production.date_planned_start_pivot, 'date_deadline': production.date_planned_start_pivot})

    def _align_pickings_dates(self):
        for production in self:
            if production.date_planned_finished_pivot and production.date_planned_start_pivot:
                for picking in production.picking_ids.filtered(lambda r: r.state not in ('done','cancel')):
                    picking.write({'scheduled_date': production.date_planned_start_pivot, 'date_deadline': production.date_planned_start_pivot})
                if production.picking_type_id.warehouse_id.manufacture_steps == 'pbm_sam':
                    for picking in production.picking_ids.filtered(lambda r: r.state not in ('done','cancel') and r.location_dest_id == production.location_src_id):
                        picking.write({'scheduled_date': production.date_planned_start_pivot, 'date_deadline': production.date_planned_start_pivot})
                    for picking in production.picking_ids.filtered(lambda r: r.state not in ('done','cancel') and r.location_id == production.location_dest_id):
                        picking.write({'scheduled_date': production.date_planned_finished_pivot, 'date_deadline': production.date_planned_finished_pivot})

    @api.depends('workorder_ids.state')
    def _get_actual_times(self):
        act_setup_time = act_teardown_time = act_working_time = act_overall_time = 0.0
        for workorder in self.workorder_ids.filtered(lambda r: r.state == "done"):
            for time in workorder.time_ids:
                act_setup_time += time.setup_duration
                act_working_time += time.working_duration
                act_teardown_time += time.teardown_duration
                act_overall_time += time.overall_duration
        self.act_setup_time = act_setup_time / 60
        self.act_teardown_time = act_teardown_time / 60
        self.act_working_time = act_working_time / 60
        self.act_overall_time = act_overall_time / 60

    def _get_uom_hours(self):
        self.hours_uom = self.env.ref('uom.product_uom_hour', raise_if_not_found=False).id

    @api.depends('bom_id', 'product_uom_qty')
    def _get_standard_times(self):
        std_setup_time = std_teardown_time = std_working_time = 0.0
        for production in self:
            for operation in production.bom_id.operation_ids:
                std_setup_time += operation.workcenter_id.time_start
                std_teardown_time += operation.workcenter_id.time_stop
                cycle_number = float_round(production.product_uom_qty / operation.workcenter_id.capacity, precision_digits=0, rounding_method='UP')
                time_cycle = operation.time_cycle
                std_working_time += (cycle_number * time_cycle * 100.0 / operation.workcenter_id.time_efficiency) / production.bom_id.product_qty
            production.std_setup_time = std_setup_time / 60
            production.std_teardown_time = std_teardown_time / 60
            production.std_working_time = std_working_time / 60
            production.std_overall_time = (std_setup_time + std_teardown_time + std_working_time) / 60

    # M-16
    # @api.onchange('bom_id')
    # def _onchange_bom_id(self):
    #     super()._onchange_bom_id()
    #     if self.bom_id and self.bom_id.picking_type_id and self.bom_id.picking_type_id != self.picking_type_id:
    #         raise UserError(_("BoM Operazione Type is not allowed."))

    ## change standard
    @api.onchange('product_id', 'picking_type_id', 'company_id')
    def _onchange_product_id(self):
        if not self.product_id:
            self.bom_id = False
        elif not self.bom_id or self.bom_id.product_tmpl_id != self.product_tmpl_id or (self.bom_id.product_id and self.bom_id.product_id != self.product_id) or self.bom_id.picking_type_id != self.picking_type_id:
            bom = self.env['mrp.bom']._bom_find(self.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id, bom_type='normal')[self.product_id]
            if bom:
                self.bom_id = bom.id
                self.product_qty = self.bom_id.product_qty
                self.product_uom_id = self.bom_id.product_uom_id.id
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id

    def _generate_backorder_productions(self, close_mo=True):
        backorders = self.env['mrp.production']
        for production in self:
            if production.backorder_sequence == 0:  # Activate backorder naming
                production.backorder_sequence = 1
            production.name = self._get_name_backorder(production.name, production.backorder_sequence)
            backorder_mo = production.copy(default=production._get_backorder_mo_vals())
            if close_mo:
                production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
                    'raw_material_production_id': backorder_mo.id,
                })
                production.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
                    'production_id': backorder_mo.id,
                })
            else:
                new_moves_vals = []
                for move in production.move_raw_ids | production.move_finished_ids:
                    if not move.additional:
                        qty_to_split = move.product_uom_qty - move.unit_factor * production.qty_producing
                        qty_to_split = move.product_uom._compute_quantity(qty_to_split, move.product_id.uom_id, rounding_method='HALF-UP')
                        move_vals = move._split(qty_to_split)
                        if not move_vals:
                            continue
                        if move.raw_material_production_id:
                            move_vals[0]['raw_material_production_id'] = backorder_mo.id
                        else:
                            move_vals[0]['production_id'] = backorder_mo.id
                        new_moves_vals.append(move_vals[0])
                self.env['stock.move'].create(new_moves_vals)
            backorders |= backorder_mo

            planned_duration_expected = unplanned_duration_expected = 0.0
            for workorder in production.workorder_ids.filtered(lambda r: r.operation_id.id != False):
                workorder.duration_expected = workorder._get_duration_expected()
                planned_duration_expected += workorder.duration_expected
            production.planned_duration_expected = planned_duration_expected / 60
            for workorder in production.workorder_ids.filtered(lambda r: r.operation_id.id == False):
                workorder.duration_expected = workorder._get_duration_expected()
                unplanned_duration_expected += workorder.duration_expected
            production.unplanned_duration_expected = unplanned_duration_expected /60

            planned_duration_expected = unplanned_duration_expected = 0.0
            for workorder in backorder_mo.workorder_ids.filtered(lambda r: r.operation_id.id != False):
                workorder.duration_expected = workorder._get_duration_expected()
                planned_duration_expected += workorder.duration_expected
            backorder_mo.planned_duration_expected = planned_duration_expected / 60
            for workorder in backorder_mo.workorder_ids.filtered(lambda r: r.operation_id.id == False):
                workorder.duration_expected = workorder._get_duration_expected()
                unplanned_duration_expected += workorder.duration_expected
            backorder_mo.unplanned_duration_expected = unplanned_duration_expected /60

        # As we have split the moves before validating them, we need to 'remove' the excess reservation
        if not close_mo:
            self.move_raw_ids.filtered(lambda m: not m.additional)._do_unreserve()
            self.move_raw_ids.filtered(lambda m: not m.additional)._action_assign()
        backorders.action_confirm()
        backorders.action_assign()

        # Remove the serial move line without reserved quantity. Post inventory will assigned all the non done moves
        # So those move lines are duplicated.
        backorders.move_raw_ids.move_line_ids.filtered(lambda ml: ml.product_id.tracking == 'serial' and ml.product_qty == 0).unlink()

        for old_wo, wo in zip(self.workorder_ids, backorders.workorder_ids):
            wo.qty_produced = max(old_wo.qty_produced - old_wo.qty_producing, 0)
            if wo.product_tracking == 'serial':
                wo.qty_producing = 1
            else:
                wo.qty_producing = wo.qty_remaining

        backorders.write({
            'qty_producing': 0.0,
        })

        return backorders
