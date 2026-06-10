# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class MrpBomComparison(models.TransientModel):
    _name = 'mrp.bom.comparison'
    _description = 'BoM Comparison'

    bom_a_id = fields.Many2one('mrp.bom', 'BoM A', required=True)
    bom_b_id = fields.Many2one('mrp.bom', 'BoM B', required=True)
    comparison_mode = fields.Selection(
        [('single', 'Single Level'),
         ('summarized', 'Multi-level Summarized')],
        string='Mode', default='single', required=True)
    line_ids = fields.One2many(
        'mrp.bom.comparison.line', 'comparison_id', 'Differences')
    diff_count = fields.Integer('Differences', compute='_compute_diff_count')

    @api.depends('line_ids.status')
    def _compute_diff_count(self):
        for comp in self:
            comp.diff_count = len(comp.line_ids.filtered(
                lambda l: l.status != 'same'))

    def _component_qtys(self, bom):
        """Return {product_id: qty} for the BoM, per the comparison mode."""
        self.ensure_one()
        result = defaultdict(float)
        if self.comparison_mode == 'summarized':
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
            _boms, lines = bom.explode(product, 1.0)
            for bom_line, data in lines:
                result[bom_line.product_id.id] += data['qty']
        else:
            for line in bom.bom_line_ids:
                # normalise to a per-unit-of-finished-product quantity
                result[line.product_id.id] += line.product_qty / (bom.product_qty or 1.0)
        return result

    def action_compare(self):
        self.ensure_one()
        if self.bom_a_id == self.bom_b_id:
            raise UserError(_("Select two different BoMs to compare."))
        self.line_ids.unlink()
        qty_a = self._component_qtys(self.bom_a_id)
        qty_b = self._component_qtys(self.bom_b_id)
        products = self.env['product.product'].browse(set(qty_a) | set(qty_b))
        vals = []
        for product in products:
            a = qty_a.get(product.id, 0.0)
            b = qty_b.get(product.id, 0.0)
            if a and b:
                status = 'same' if float_compare(
                    a, b, precision_digits=6) == 0 else 'changed'
            elif b:
                status = 'added'
            else:
                status = 'removed'
            vals.append({
                'comparison_id': self.id,
                'product_id': product.id,
                'qty_a': a,
                'qty_b': b,
                'qty_diff': b - a,
                'status': status,
            })
        self.env['mrp.bom.comparison.line'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom.comparison',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class MrpBomComparisonLine(models.TransientModel):
    _name = 'mrp.bom.comparison.line'
    _description = 'BoM Comparison Line'
    _order = 'status, id'

    comparison_id = fields.Many2one(
        'mrp.bom.comparison', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Component')
    qty_a = fields.Float('Qty in A', digits='Product Unit Of Measure')
    qty_b = fields.Float('Qty in B', digits='Product Unit Of Measure')
    qty_diff = fields.Float('Delta', digits='Product Unit Of Measure')
    status = fields.Selection(
        [('same', 'Unchanged'),
         ('added', 'Added'),
         ('removed', 'Removed'),
         ('changed', 'Qty Changed')],
        string='Status')
