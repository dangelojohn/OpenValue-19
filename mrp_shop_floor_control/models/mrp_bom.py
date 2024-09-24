# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    def open_bom(self):
        self.ensure_one()
        if self.child_bom_id:
            return {
                "res_id": self.child_bom_id.id,
                "domain": "[('id','=', " + str(self.child_bom_id.id) + ")]",
                "name": _("BOM"),
                "view_type": "form",
                "view_mode": "form,tree",
                "res_model": "mrp.bom",
                "view_id": False,
                "target": "current",
                "type": "ir.actions.act_window",
            }

