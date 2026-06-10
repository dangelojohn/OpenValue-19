# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class MrpPlanningRun(models.Model):
    _inherit = 'mrp.planning.run'

    def action_run(self):
        res = super().action_run()
        Bom = self.env['mrp.bom']
        for line in self.line_ids.filtered(lambda l: l.supply_type == 'manufacture'):
            bom = Bom._bom_find(line.product_id)[line.product_id]
            if bom and bom.type == 'subcontract':
                line.supply_type = 'subcontract'
        return res


class MrpPlanningLine(models.Model):
    _inherit = 'mrp.planning.line'

    supply_type = fields.Selection(
        selection_add=[('subcontract', 'Subcontract')],
        ondelete={'subcontract': 'set null'})

    def action_release(self):
        Bom = self.env['mrp.bom']
        subcontract = self.filtered(
            lambda l: l.supply_type == 'subcontract' and not l.released)
        for line in subcontract:
            bom = Bom._bom_find(line.product_id)[line.product_id]
            subcontractor = bom.subcontractor_ids[:1] if bom else False
            if not subcontractor:
                raise UserError(_(
                    "No subcontractor on the subcontracting BoM of %s.",
                    line.product_id.display_name))
            po = self.env['purchase.order'].create({
                'partner_id': subcontractor.id,
                'order_line': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.suggested_qty,
                    'product_uom_id': line.product_id.uom_id.id,
                    'price_unit': line.product_id.standard_price,
                    'name': line.product_id.display_name,
                    'date_planned': fields.Datetime.now(),
                })],
            })
            line.generated_ref = 'purchase.order,%s' % po.id
            line.released = True
        others = self - subcontract
        if others:
            return super(MrpPlanningLine, others).action_release()
        return True
