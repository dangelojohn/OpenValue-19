# -*- coding: utf-8 -*-

from odoo import models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_open_scheduling_engine(self):
        """Open a draft scheduling run pre-filled with the selected MOs."""
        run = self.env['mrp.scheduling.run'].create({
            'production_ids': [(6, 0, self.ids)],
        })
        return {
            'name': _('SFC Scheduling Engine'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.scheduling.run',
            'view_mode': 'form',
            'res_id': run.id,
            'target': 'current',
        }
