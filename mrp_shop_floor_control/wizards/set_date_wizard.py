# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SetDateWizard(models.TransientModel):
    _name = 'set.date.wizard'
    _description = "Mid Point Scheduling Wizard"

    new_date_planned_start_wo = fields.Datetime('New Scheduled Start Date', required=True)
    workorder_id = fields.Many2one('mrp.workorder', string="Work Order", readonly=True)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            defaults['workorder_id'] = active_id
        return defaults

    def set_date(self):
        self.ensure_one()
        workorder = self.workorder_id
        if not workorder:
            raise UserError(_('No work order selected.'))
        if workorder.state == 'progress':
            raise UserError(_('Mid point scheduling cannot be performed for a work order in progress.'))
        if not workorder.date_planned_start_wo:
            raise UserError(_('This work order has not been scheduled yet.'))
        calendar = workorder.workcenter_id.resource_calendar_id
        new_date = self.new_date_planned_start_wo
        if calendar:
            new_date = calendar.plan_hours(0.0, new_date, compute_leaves=True)
        workorder.date_planned_start_wo = new_date
        workorder.mid_point_scheduling_engine()
        return True
