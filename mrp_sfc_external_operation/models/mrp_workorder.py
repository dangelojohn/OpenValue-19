# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    is_external = fields.Boolean(
        'External Operation', related='operation_id.is_external', store=True)
    external_po_line_id = fields.Many2one(
        'purchase.order.line', 'External PO Line', copy=False)
    external_po_id = fields.Many2one(
        'purchase.order', 'External PO',
        related='external_po_line_id.order_id', store=True)
    external_po_state = fields.Selection(
        related='external_po_id.state', string='External PO Status')

    def action_external_done(self):
        """Complete an outsourced work order. There is no in-house time on an
        external operation, so we mark it done with its output quantity but
        without registering any work-center time (its cost comes from the
        purchase order, not in-house labour). This lets the manufacturing order
        reach 'done' even though the operation was subcontracted."""
        for workorder in self.filtered(
                lambda w: w.is_external and w.state not in ('done', 'cancel')):
            if not workorder.qty_output_wo:
                workorder.qty_output_wo = workorder.qty_production
            # button_finish marks the WO done; with no time_ids it records no
            # in-house cost.
            workorder.button_finish()
        return True
