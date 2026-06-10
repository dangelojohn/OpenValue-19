# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import fields, models, _


class MrpMpsReport(models.TransientModel):
    _name = 'mrp.mps.report'
    _description = 'Master Production Plan Feasibility'

    date_from = fields.Datetime(
        'From', required=True, default=fields.Datetime.now)
    date_to = fields.Datetime(
        'To', required=True,
        default=lambda self: fields.Datetime.now() + timedelta(days=14))
    only_draft = fields.Boolean(
        'Draft Orders Only', default=False,
        help="Restrict to draft orders (not yet confirmed).")

    def action_check(self):
        """Run the availability check over every order in the window and open
        the result list."""
        self.ensure_one()
        states = ['draft'] if self.only_draft else None
        orders = self.env['mrp.production'].check_availability_for_range(
            self.date_from, self.date_to, states=states)
        return {
            'name': _('Master Production Plan'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('id', 'in', orders.ids)],
            'views': [
                (self.env.ref('mrp_sfc_availability_check.view_mps_production_list').id, 'list'),
                (False, 'form'),
            ],
        }
