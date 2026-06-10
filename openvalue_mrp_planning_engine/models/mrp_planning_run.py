# -*- coding: utf-8 -*-

import math

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpPlanningRun(models.Model):
    _name = 'mrp.planning.run'
    _description = 'MRP Planning Run'
    _order = 'create_date desc'

    name = fields.Char('Reference', default=lambda self: _('New'), copy=False)
    date = fields.Date('Planning Date', default=fields.Date.today, required=True)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse', required=True,
        default=lambda self: self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1))
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Planned')], default='draft', copy=False)
    line_ids = fields.One2many(
        'mrp.planning.line', 'run_id', 'Planned Orders', copy=False)
    line_count = fields.Integer('Lines', compute='_compute_line_count')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for run in self:
            run.line_count = len(run.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'mrp.planning.run') or _('New')
        return super().create(vals_list)

    def action_run(self):
        self.ensure_one()
        self.line_ids.unlink()
        orderpoints = self.env['stock.warehouse.orderpoint'].search([
            ('warehouse_id', '=', self.warehouse_id.id),
            ('company_id', '=', self.company_id.id),
        ])
        Bom = self.env['mrp.bom']
        vals = []
        for op in orderpoints:
            product = op.product_id
            forecast = product.with_context(
                warehouse=self.warehouse_id.id).virtual_available
            if forecast >= op.product_min_qty:
                continue
            target = max(op.product_max_qty, op.product_min_qty)
            qty = target - forecast
            multiple = getattr(op, 'qty_multiple', 0) or 0
            if multiple:
                qty = math.ceil(qty / multiple) * multiple
            if qty <= 0:
                continue
            bom = Bom._bom_find(product)[product]
            vals.append({
                'run_id': self.id,
                'product_id': product.id,
                'forecast_qty': forecast,
                'min_qty': op.product_min_qty,
                'max_qty': op.product_max_qty,
                'suggested_qty': qty,
                'supply_type': 'manufacture' if bom else 'buy',
                'planned_date': self.date,
            })
        self.env['mrp.planning.line'].create(vals)
        self.state = 'done'
        return True


class MrpPlanningLine(models.Model):
    _name = 'mrp.planning.line'
    _description = 'MRP Planning Line'
    _order = 'supply_type, id'

    run_id = fields.Many2one(
        'mrp.planning.run', 'Planning Run', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    forecast_qty = fields.Float('Forecast', digits='Product Unit of Measure')
    min_qty = fields.Float('Min', digits='Product Unit of Measure')
    max_qty = fields.Float('Max', digits='Product Unit of Measure')
    suggested_qty = fields.Float('Suggested Qty', digits='Product Unit of Measure')
    supply_type = fields.Selection(
        [('buy', 'Purchase'), ('manufacture', 'Manufacture')], string='Supply')
    planned_date = fields.Date('Planned Date')
    released = fields.Boolean('Released', copy=False)
    generated_ref = fields.Reference(
        selection=[('mrp.production', 'Manufacturing Order'),
                   ('purchase.order', 'Purchase Order')],
        string='Generated Document', copy=False)

    def action_release(self):
        for line in self:
            if line.released:
                continue
            if line.supply_type == 'manufacture':
                doc = self.env['mrp.production'].create({
                    'product_id': line.product_id.id,
                    'product_qty': line.suggested_qty,
                })
                line.generated_ref = 'mrp.production,%s' % doc.id
            else:
                seller = line.product_id._select_seller(quantity=line.suggested_qty)
                if not seller:
                    raise UserError(_(
                        "No vendor configured for %s; cannot raise a purchase "
                        "order.", line.product_id.display_name))
                po = self.env['purchase.order'].create({
                    'partner_id': seller.partner_id.id,
                    'order_line': [(0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.suggested_qty,
                        'product_uom_id': line.product_id.uom_id.id,
                        'price_unit': seller.price,
                        'name': line.product_id.display_name,
                        'date_planned': fields.Datetime.now(),
                    })],
                })
                line.generated_ref = 'purchase.order,%s' % po.id
            line.released = True
        return True
