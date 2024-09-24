# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime
from odoo.tools import float_round


class MrpStarting(models.TransientModel):
    _name = 'mrp.starting'
    _description = "MRP Starting"


    production_id = fields.Many2one('mrp.production', 'Production Order', domain=[('picking_type_id.active', '=', True), ('workorder_ids', 'not in', []),('state', 'in', ('confirmed','progress'))])
    workorder_id = fields.Many2one('mrp.workorder', "Workorder", domain="[('state', 'not in', ['progress','done','cancel']), ('production_id','=',production_id)]")
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    milestone = fields.Boolean('Milestone', related='workorder_id.milestone')
    date_start = fields.Datetime('Start Date', required=True, default=lambda self: fields.datetime.now())

    @api.model
    def default_get(self, fields):
        default = super().default_get(fields)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            default['production_id'] = active_id
        return default

    @api.onchange('production_id')
    def onchange_production_id(self):
        workorder_domain = [('state', 'not in', ['done', 'cancel', 'progress'])]
        if self.production_id:
            workorder_domain += [('production_id', '=', self.production_id.id)]
            workorder_ids = self.env['mrp.workorder'].search(workorder_domain)
            if workorder_ids:
                if self.workorder_id and self.workorder_id.id not in workorder_ids.ids:
                    self.workorder_id = False

    def do_starting(self):
        workorders = self.workorder_id.production_id.workorder_ids
        wo_sequence = self.workorder_id.sequence
        prev_workorders = [x for x in workorders if x.sequence < wo_sequence]
        if self.workorder_id.milestone:
            if any(prev_workorder.state == 'progress' for prev_workorder in prev_workorders):
                raise UserError(_('previous workorders in progress'))
            for prev_workorder in prev_workorders:
                if prev_workorder.state in ('ready','pending','waiting'):
                    prev_workorder.state = 'cancel'
                wo_capacity_id = self.env['mrp.workcenter.capacity'].search([('workorder_id', '=', prev_workorder.id)],limit=1)
                if wo_capacity_id:
                    wo_capacity_id.unlink()
            self._set_wo_inprogress(self.workorder_id)
        else:
            if any(prev_workorder.state not in  ('done','cancel') for prev_workorder in prev_workorders):
                raise UserError(_('previous workorders not closed or calcelled'))
            self._set_wo_inprogress(self.workorder_id)
        return True

    def _set_wo_inprogress(self, workorder):
        workorder.button_start()
        time_id = self.env['mrp.workcenter.productivity'].search([('workorder_id','=', workorder.id),('date_end','=',False)], limit=1)
        if time_id:
            time_id.date_start = self.date_start
        return True