# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    external_po_line_ids = fields.One2many(
        'purchase.order.line', 'production_id', 'External PO Lines', copy=False)
    external_po_count = fields.Integer(
        'External POs', compute='_compute_external_po_count')
    external_operation_count = fields.Integer(
        'External Operations', compute='_compute_external_operation_count')

    @api.depends('external_po_line_ids.order_id')
    def _compute_external_po_count(self):
        for production in self:
            production.external_po_count = len(
                production.external_po_line_ids.order_id)

    @api.depends('workorder_ids.is_external')
    def _compute_external_operation_count(self):
        for production in self:
            production.external_operation_count = len(
                production.workorder_ids.filtered('is_external'))

    def action_create_external_pos(self):
        """Generate purchase orders for every external work order that does not
        yet have one. One PO per vendor, one line per work order."""
        Purchase = self.env['purchase.order']
        POLine = self.env['purchase.order.line']
        created = self.env['purchase.order']
        for production in self:
            pending = production.workorder_ids.filtered(
                lambda w: w.is_external and not w.external_po_line_id)
            if not pending:
                continue
            by_vendor = defaultdict(lambda: self.env['mrp.workorder'])
            for workorder in pending:
                operation = workorder.operation_id
                if not operation.external_partner_id:
                    raise UserError(_(
                        "Operation '%s' is external but has no subcontractor.",
                        operation.name))
                if not operation.external_service_product_id:
                    raise UserError(_(
                        "Operation '%s' is external but has no service product.",
                        operation.name))
                by_vendor[operation.external_partner_id.id] |= workorder
            for vendor_id, workorders in by_vendor.items():
                vendor = self.env['res.partner'].browse(vendor_id)
                po = Purchase.create({
                    'partner_id': vendor.id,
                    'origin': production.name,
                })
                for workorder in workorders:
                    operation = workorder.operation_id
                    product = operation.external_service_product_id
                    qty = workorder.qty_output_wo or production.product_qty
                    price = operation.external_price or product.standard_price
                    line = POLine.create({
                        'order_id': po.id,
                        'product_id': product.id,
                        'name': "%s - %s" % (production.name, operation.name),
                        'product_qty': qty,
                        'product_uom_id': product.uom_id.id,
                        'price_unit': price,
                        'date_planned': production.date_start or fields.Datetime.now(),
                        'production_id': production.id,
                        'workorder_id': workorder.id,
                    })
                    workorder.external_po_line_id = line.id
                created |= po
        if not created:
            raise UserError(_(
                "No external work orders awaiting a purchase order were found."))
        return self.action_view_external_pos()

    def action_view_external_pos(self):
        self.ensure_one()
        pos = self.external_po_line_ids.order_id
        action = {
            'name': _('External Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'domain': [('id', 'in', pos.ids)],
            'view_mode': 'list,form',
        }
        if len(pos) == 1:
            action.update({'view_mode': 'form', 'res_id': pos.id})
        return action
