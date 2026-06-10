# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class MaintenancePlan(models.Model):
    _name = 'maintenance.plan'
    _description = 'Maintenance Plan'
    _order = 'next_date, id'

    name = fields.Char('Plan', required=True)
    active = fields.Boolean(default=True)
    equipment_id = fields.Many2one(
        'maintenance.equipment', 'Equipment', required=True, ondelete='cascade')
    maintenance_type = fields.Selection(
        [('corrective', 'Corrective'),
         ('preventive', 'Preventive'),
         ('on_condition', 'On Condition'),
         ('periodic', 'Periodic'),
         ('retrofit', 'Retrofit')],
        string='Strategy', default='periodic', required=True)
    interval_number = fields.Integer('Every', default=1, required=True)
    interval_type = fields.Selection(
        [('day', 'Days'), ('week', 'Weeks'), ('month', 'Months')],
        string='Interval Unit', default='month', required=True)
    next_date = fields.Date('Next Date', default=fields.Date.today)
    maintenance_team_id = fields.Many2one('maintenance.team', 'Team')
    technician_user_id = fields.Many2one('res.users', 'Technician')
    request_count = fields.Integer('Requests', compute='_compute_request_count')
    request_ids = fields.One2many(
        'maintenance.request', 'maintenance_plan_id', 'Requests')

    def _compute_request_count(self):
        for plan in self:
            plan.request_count = len(plan.request_ids)

    def _advance_next_date(self):
        for plan in self:
            base = plan.next_date or fields.Date.today()
            unit = {'day': 'days', 'week': 'weeks', 'month': 'months'}[plan.interval_type]
            plan.next_date = base + relativedelta(**{unit: plan.interval_number})

    def action_generate_request(self):
        Request = self.env['maintenance.request']
        created = Request
        for plan in self:
            vals = {
                'name': "%s - %s" % (
                    plan.name,
                    fields.Date.to_string(plan.next_date or fields.Date.today())),
                'equipment_id': plan.equipment_id.id,
                'maintenance_type': plan.maintenance_type,
                'request_date': fields.Date.today(),
                'schedule_date': plan.next_date or fields.Date.today(),
                'maintenance_plan_id': plan.id,
            }
            if plan.maintenance_team_id:
                vals['maintenance_team_id'] = plan.maintenance_team_id.id
            if plan.technician_user_id:
                vals['technician_user_id'] = plan.technician_user_id.id
            created |= Request.create(vals)
            plan._advance_next_date()
        return {
            'name': _('Maintenance Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
        }


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    maintenance_plan_id = fields.Many2one(
        'maintenance.plan', 'Maintenance Plan', ondelete='set null')
