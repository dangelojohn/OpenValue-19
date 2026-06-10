# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InterwarehouseTransfer(models.TransientModel):
    _name = 'interwarehouse.transfer'
    _description = 'Interwarehouse Transfer'

    source_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Source Warehouse', required=True)
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Destination Warehouse', required=True)
    product_id = fields.Many2one(
        'product.product', 'Product', required=True,
        domain=[('is_storable', '=', True)])
    product_uom_qty = fields.Float('Quantity', required=True, default=1.0)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit', compute='_compute_uom', store=True, readonly=False)
    scheduled_date = fields.Datetime('Scheduled Date', default=fields.Datetime.now)

    @api.depends('product_id')
    def _compute_uom(self):
        for wiz in self:
            wiz.product_uom_id = wiz.product_id.uom_id

    def action_transfer(self):
        self.ensure_one()
        if self.source_warehouse_id == self.dest_warehouse_id:
            raise UserError(_("Source and destination warehouses must differ."))
        if self.product_uom_qty <= 0:
            raise UserError(_("Quantity must be positive."))
        src = self.source_warehouse_id.lot_stock_id
        dst = self.dest_warehouse_id.lot_stock_id
        picking_type = self.source_warehouse_id.int_type_id
        if not picking_type:
            raise UserError(_(
                "No internal transfer operation type on the source warehouse."))
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': src.id,
            'location_dest_id': dst.id,
            'scheduled_date': self.scheduled_date or fields.Datetime.now(),
            'origin': _('Interwarehouse Transfer'),
            'move_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_qty': self.product_uom_qty,
                'product_uom': self.product_uom_id.id,
                'location_id': src.id,
                'location_dest_id': dst.id,
            })],
        })
        picking.action_confirm()
        return {
            'name': _('Interwarehouse Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': picking.id,
        }
