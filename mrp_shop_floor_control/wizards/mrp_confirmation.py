# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class MrpConfirmation(models.TransientModel):
    _name = 'mrp.confirmation'
    _description = "Work Order Confirmation"

    date_start = fields.Datetime('Start Date', required=True)
    date_end = fields.Datetime('End Date', compute='_compute_date_end')
    setup_duration = fields.Float('Setup Duration')
    teardown_duration = fields.Float('Cleanup Duration')
    working_duration = fields.Float('Working Duration', required=True)
    overall_duration = fields.Float('Overall Duration', compute='_compute_overall_duration')
    production_id = fields.Many2one(
        'mrp.production', 'Production Order',
        domain=[('state', 'in', ('confirmed', 'progress')), ('workorder_ids', '!=', False)])
    product_id = fields.Many2one('product.product', 'Product', related='production_id.product_id', readonly=True)
    tracking = fields.Selection(related='product_id.tracking')
    final_lot_id = fields.Many2one('stock.lot', "Lot/Serial Number")
    workorder_id = fields.Many2one(
        'mrp.workorder', "Work Order",
        domain="[('state', 'not in', ['done', 'cancel']), ('production_id', '=', production_id)]")
    qty_production = fields.Float(
        'Manufacturing Order Qty', readonly=True, related='workorder_id.qty_production')
    qty_output_wo = fields.Float('WO Quantity', digits='Product Unit')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure', related='production_id.product_uom_id', readonly=True)
    user_id = fields.Many2one(
        'res.users', string='User', required=True, default=lambda self: self.env.user)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, default=lambda self: self.env.company)
    milestone = fields.Boolean('Milestone', related='workorder_id.milestone')

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            defaults['production_id'] = active_id
        return defaults

    @api.depends('setup_duration', 'teardown_duration', 'working_duration')
    def _compute_overall_duration(self):
        for record in self:
            record.overall_duration = (
                record.setup_duration + record.teardown_duration + record.working_duration)

    @api.depends('overall_duration', 'date_start', 'workorder_id')
    def _compute_date_end(self):
        for record in self:
            if not (record.date_start and record.overall_duration):
                record.date_end = False
                continue
            calendar = record.workorder_id.workcenter_id.resource_calendar_id
            if calendar:
                start = calendar.plan_hours(0.0, record.date_start, compute_leaves=True)
                record.date_end = calendar.plan_hours(
                    record.overall_duration / 60.0, start, compute_leaves=True)
            else:
                record.date_end = record.date_start + timedelta(minutes=record.overall_duration)

    @api.constrains('qty_output_wo')
    def _check_qty_output_wo(self):
        for record in self:
            if record.qty_output_wo <= 0.0:
                raise UserError(_('Quantity must be positive.'))
            if record.product_id.tracking == 'serial' and record.qty_output_wo > 1.0:
                raise UserError(_('Confirmed quantity must be 1 for a serial-tracked product.'))

    @api.onchange('production_id')
    def _onchange_production_id(self):
        if self.production_id and self.workorder_id.production_id != self.production_id:
            self.workorder_id = False

    @api.onchange('workorder_id')
    def _onchange_workorder_id(self):
        workorder = self.workorder_id
        if not workorder:
            return
        self.qty_output_wo = workorder._get_maximum_quantity()
        if workorder.prev_work_order_id.date_actual_finished_wo:
            self.date_start = workorder.prev_work_order_id.date_actual_finished_wo
        else:
            self.date_start = (workorder.date_planned_start_wo
                               or self.production_id.date_planned_start_pivot
                               or fields.Datetime.now())
        if workorder.state == 'progress':
            time_record = self.env['mrp.workcenter.productivity'].search(
                [('workorder_id', '=', workorder.id), ('date_end', '=', False)], limit=1)
            if time_record:
                self.date_start = time_record.date_start

    @api.onchange('workorder_id', 'qty_output_wo')
    def _onchange_durations(self):
        workorder = self.workorder_id
        if not workorder or not workorder.workcenter_id:
            return
        workcenter = workorder.workcenter_id
        capacity = workcenter._sfc_capacity(self.product_id) or 1.0
        efficiency = workcenter.time_efficiency or 100.0
        prod_qty = self.production_id.product_uom_qty
        prod_cycle = float_round(prod_qty / capacity, precision_digits=0, rounding_method='UP') or 1.0
        working_per_cycle = ((workorder.duration_expected - workcenter.time_start - workcenter.time_stop)
                             * efficiency / (100.0 * prod_cycle))
        working_per_cycle = max(working_per_cycle, 0.0)
        qty = self.product_uom_id._compute_quantity(
            self.qty_output_wo, self.product_id.uom_id) if self.product_uom_id else self.qty_output_wo
        cycle_number = float_round(qty / capacity, precision_digits=0, rounding_method='UP')
        self.working_duration = working_per_cycle * cycle_number * 100.0 / efficiency
        self.setup_duration = workcenter.time_start
        self.teardown_duration = workcenter.time_stop

    def _reopen_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_generate_serial(self):
        self.ensure_one()
        self.final_lot_id = self.env['stock.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.production_id.company_id.id,
        })
        return self._reopen_form()

    def do_confirm(self):
        self.ensure_one()
        workorder = self.workorder_id
        if not workorder:
            raise UserError(_('Please select a work order.'))
        if workorder.state in ('blocked', 'ready'):
            workorder.button_start()
        time_record = self.env['mrp.workcenter.productivity'].search(
            [('workorder_id', '=', workorder.id), ('date_end', '=', False)], limit=1)
        if not time_record:
            raise UserError(_('No open time record was found for this work order.'))
        time_record.write({
            'setup_duration': self.setup_duration,
            'teardown_duration': self.teardown_duration,
            'working_duration': self.working_duration,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'user_id': self.user_id.id,
        })
        if self.final_lot_id:
            workorder.finished_lot_ids = [fields.Command.set(self.final_lot_id.ids)]
        workorder.qty_output_wo = self.qty_output_wo
        workorder.button_finish()
        return True
