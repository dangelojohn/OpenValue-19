# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models, _


class StockTurnoverReport(models.TransientModel):
    _name = 'stock.turnover.report'
    _description = 'Inventory Turnover Report'

    date_from = fields.Date(
        'From', required=True,
        default=lambda self: fields.Date.today() - timedelta(days=90))
    date_to = fields.Date('To', required=True, default=fields.Date.today)
    categ_id = fields.Many2one('product.category', 'Product Category')
    line_ids = fields.One2many(
        'stock.turnover.report.line', 'report_id', 'Results')

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        domain = [('is_storable', '=', True)]
        if self.categ_id:
            domain.append(('categ_id', '=', self.categ_id.id))
        products = self.env['product.product'].search(domain)
        dt_from = fields.Datetime.to_datetime(self.date_from)
        dt_to = fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)
        Move = self.env['stock.move']
        vals = []
        for product in products:
            moves = Move.search([
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
                ('date', '>=', dt_from),
                ('date', '<', dt_to),
            ])
            out_qty = sum(
                m.product_qty for m in moves
                if m.location_id.usage == 'internal'
                and m.location_dest_id.usage != 'internal')
            in_qty = sum(
                m.product_qty for m in moves
                if m.location_dest_id.usage == 'internal'
                and m.location_id.usage != 'internal')
            # True period average: begin = end - net change over the period,
            # then average the opening and closing on-hand quantities.
            end_qty = product.qty_available or 0.0
            begin_qty = end_qty - (in_qty - out_qty)
            avg_inventory = (begin_qty + end_qty) / 2.0
            turnover = (out_qty / avg_inventory) if avg_inventory else 0.0
            if out_qty or avg_inventory:
                vals.append({
                    'report_id': self.id,
                    'product_id': product.id,
                    'out_qty': out_qty,
                    'avg_inventory': avg_inventory,
                    'turnover': turnover,
                })
        self.env['stock.turnover.report.line'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.turnover.report',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class StockTurnoverReportLine(models.TransientModel):
    _name = 'stock.turnover.report.line'
    _description = 'Inventory Turnover Report Line'
    _order = 'turnover desc'

    report_id = fields.Many2one(
        'stock.turnover.report', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product')
    out_qty = fields.Float('Outbound Qty', digits='Product Unit of Measure')
    avg_inventory = fields.Float('Avg Inventory', digits='Product Unit of Measure')
    turnover = fields.Float('Turnover', digits=(12, 2))
