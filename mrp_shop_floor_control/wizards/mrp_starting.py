# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpStarting(models.TransientModel):
    _name = 'mrp.starting'
    _description = "Work Order Starting"

    production_id = fields.Many2one(
        'mrp.production', 'Production Order',
        domain=[('state', 'in', ('confirmed', 'progress')), ('workorder_ids', '!=', False)])
    workorder_id = fields.Many2one(
        'mrp.workorder', "Work Order",
        domain="[('state', 'not in', ['progress', 'done', 'cancel']), "
               "('production_id', '=', production_id)]")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, default=lambda self: self.env.company)
    milestone = fields.Boolean('Milestone', related='workorder_id.milestone')
    date_start = fields.Datetime('Start Date', required=True, default=fields.Datetime.now)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            defaults['production_id'] = active_id
        return defaults

    @api.onchange('production_id')
    def _onchange_production_id(self):
        if self.production_id and self.workorder_id.production_id != self.production_id:
            self.workorder_id = False

    def do_starting(self):
        self.ensure_one()
        workorder = self.workorder_id
        if not workorder:
            raise UserError(_('Please select a work order.'))
        prev = workorder.production_id.workorder_ids.filtered(
            lambda w: w.sfc_sequence < workorder.sfc_sequence)
        if workorder.milestone:
            if any(w.state == 'progress' for w in prev):
                raise UserError(_('A preceding work order is in progress.'))
            for prev_wo in prev:
                if prev_wo.state in ('blocked', 'ready'):
                    prev_wo.state = 'cancel'
                self.env['mrp.workcenter.load'].search(
                    [('workorder_id', '=', prev_wo.id)]).unlink()
        elif any(w.state not in ('done', 'cancel') for w in prev):
            raise UserError(_('Preceding work orders are not closed or cancelled.'))
        self._set_workorder_in_progress(workorder)
        return True

    def _set_workorder_in_progress(self, workorder):
        workorder.button_start()
        time_record = self.env['mrp.workcenter.productivity'].search(
            [('workorder_id', '=', workorder.id), ('date_end', '=', False)], limit=1)
        if time_record:
            time_record.date_start = self.date_start
        return True
