# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'


    def mid_point_scheduling_engine(self):
        for workorder in self:
            sequence_wo = workorder.sequence
            workorder.forwards_scheduling()
            min_date_start = workorder.date_planned_start_wo
            max_date_finished = workorder.date_planned_finished_wo

            parall_workorders = self.env['mrp.workorder'].search([
                ('production_id', '=', workorder.production_id.id),
                ('state', 'in', ('ready','pending', 'waiting')),
                ('sequence', '=', sequence_wo),
                ('id', '!=', workorder.id),
                ])
            if parall_workorders:
                for parall_workorder in parall_workorders:
                    parall_workorder.date_planned_start_wo = workorder.date_planned_start_wo
                    parall_workorder.forwards_scheduling()
                    max_date_finished = max(parall_workorder.date_planned_finished_wo, max_date_finished)

            parall_progress_workorders = self.env['mrp.workorder'].search([
                ('production_id', '=', workorder.production_id.id),
                ('state', '=', 'progress'),
                ('sequence', '=', sequence_wo),
                ('id', '!=', workorder.id),
                ])
            if parall_progress_workorders:
                for progress_workorder in parall_progress_workorders:
                    max_date_finished = max(progress_workorder.date_planned_finished_wo, max_date_finished)

            prev_workorders = self.env['mrp.workorder'].search([
                ('production_id', '=', workorder.production_id.id),
                ('state', 'in', ('ready','pending', 'progress', 'waiting')),
                ('sequence', '<', sequence_wo),
                ]).sorted(key=lambda r: (r.sequence, r.duration_expected), reverse=True)
            if prev_workorders:
                current_workorder = workorder
                for prev_workorder in prev_workorders:
                    # workorder precedente in progress
                    if prev_workorder.state == 'progress':
                        if prev_workorder.date_planned_finished_wo > current_workorder.date_planned_start_wo:
                            raise UserError(_('backward scheduling is not possible for the production order %r' %workorder.production_id.name))
                    else:
                        # workorder in parallelo
                        if current_workorder.sequence == prev_workorder.sequence:
                            prev_workorder.date_planned_start_wo = current_workorder.date_planned_start_wo
                            prev_workorder.forwards_scheduling()
                        # workorder in sequenza
                        else:
                            prev_workorder.date_planned_finished_wo = min_date_start
                            prev_workorder.backwards_scheduling()
                    min_date_start = min(prev_workorder.date_planned_start_wo, current_workorder.date_planned_start_wo)
                    current_workorder = prev_workorder

            succ_workorders = self.env['mrp.workorder'].search([
                ('production_id', '=', workorder.production_id.id),
                ('state', 'in', ('ready','pending', 'waiting')),
                ('sequence', '>', sequence_wo),
                ]).sorted(key=lambda r: r.sequence)
            if succ_workorders:
                current_workorder = workorder
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

            workorder.production_id.date_planned_start_wo = min_date_start
            workorder.production_id.date_planned_finished_wo = max_date_finished


class set_date_wizard(models.TransientModel):
    _name = 'set.date.wizard'
    _description = "Mid Point Scheduling Wizard"

    new_date_planned_start_wo = fields.Datetime(string=_('New Scheduled Start Date'), required=True)
    workorder_id = fields.Many2one('mrp.workorder', string="Workorder", readonly=True)

    @api.model
    def default_get(self, fields):
        default = super().default_get(fields)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            default['workorder_id'] = active_id
        return default

    def set_date(self):
        new_date_planned = False
        workorder_id = self.env.context.get('active_id', False)
        if workorder_id:
            workorder = self.env['mrp.workorder'].browse(workorder_id)
            if workorder.state == 'progress':
                raise UserError(_('midpoint scheduling cannot be performed for workorder in progress'))
            if not workorder.date_planned_start_wo:
                raise UserError(_('Manufacturing Order not scheduled yet'))
            calendar = workorder.workcenter_id.resource_calendar_id
            new_date_planned = calendar.plan_hours(0.0, self.new_date_planned_start_wo, True)
            workorder.write({'date_planned_start_wo': new_date_planned})
            workorder.mid_point_scheduling_engine()
