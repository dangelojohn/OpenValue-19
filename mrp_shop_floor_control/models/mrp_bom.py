# -*- coding: utf-8 -*-

from odoo import models, _


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    def open_bom(self):
        """Open the child BoM linked to this component line."""
        self.ensure_one()
        if not self.child_bom_id:
            return False
        return {
            'name': _("Bill of Materials"),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'res_id': self.child_bom_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
