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
