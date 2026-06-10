# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    equipment_ids = fields.One2many(
        'maintenance.equipment', 'workcenter_id', 'Equipment')
    maintenance_request_count = fields.Integer(
        'Open Maintenance Requests', compute='_compute_maintenance_request_count')

    @api.depends('equipment_ids')
    def _compute_maintenance_request_count(self):
        Request = self.env['maintenance.request']
        for workcenter in self:
            if workcenter.equipment_ids:
                workcenter.maintenance_request_count = Request.search_count([
                    ('equipment_id', 'in', workcenter.equipment_ids.ids),
                    ('stage_id.done', '=', False),
                ])
            else:
                workcenter.maintenance_request_count = 0

    def action_view_maintenance_requests(self):
        self.ensure_one()
        return {
            'name': _('Maintenance Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'list,form',
            'domain': [('equipment_id', 'in', self.equipment_ids.ids)],
            'context': {'default_equipment_id': self.equipment_ids[:1].id},
        }
