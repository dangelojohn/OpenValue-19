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
         ('level', 'Multi-level Level by Level'),
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

    @staticmethod
    def _diff_status(a, b):
        if a and b:
            return 'same' if float_compare(a, b, precision_digits=6) == 0 else 'changed'
        return 'added' if b else 'removed'

    def _compare_level(self, bom_a, bom_b, level, path, vals):
        """Recursively compare the direct lines of two BoMs, descending into
        manufactured sub-assemblies present on either side."""
        a_lines = {l.product_id.id: l for l in bom_a.bom_line_ids} if bom_a else {}
        b_lines = {l.product_id.id: l for l in bom_b.bom_line_ids} if bom_b else {}
        for product in self.env['product.product'].browse(set(a_lines) | set(b_lines)):
            la, lb = a_lines.get(product.id), b_lines.get(product.id)
            qa = la.product_qty / (bom_a.product_qty or 1.0) if la else 0.0
            qb = lb.product_qty / (bom_b.product_qty or 1.0) if lb else 0.0
            vals.append({
                'comparison_id': self.id,
                'product_id': product.id,
                'qty_a': qa,
                'qty_b': qb,
                'qty_diff': qb - qa,
                'status': self._diff_status(qa, qb),
                'level': level,
                'bom_path': path or '/',
            })
            sub_a = la.child_bom_id if la else False
            sub_b = lb.child_bom_id if lb else False
            if sub_a or sub_b:
                self._compare_level(
                    sub_a, sub_b, level + 1,
                    '%s/%s' % (path, product.display_name), vals)

    def action_compare(self):
        self.ensure_one()
        if self.bom_a_id == self.bom_b_id:
            raise UserError(_("Select two different BoMs to compare."))
        self.line_ids.unlink()
        vals = []
        if self.comparison_mode == 'level':
            self._compare_level(self.bom_a_id, self.bom_b_id, 0, '', vals)
        else:
            qty_a = self._component_qtys(self.bom_a_id)
            qty_b = self._component_qtys(self.bom_b_id)
            for product in self.env['product.product'].browse(set(qty_a) | set(qty_b)):
                a = qty_a.get(product.id, 0.0)
                b = qty_b.get(product.id, 0.0)
                vals.append({
                    'comparison_id': self.id,
                    'product_id': product.id,
                    'qty_a': a,
                    'qty_b': b,
                    'qty_diff': b - a,
                    'status': self._diff_status(a, b),
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
    _order = 'level, status, id'

    comparison_id = fields.Many2one(
        'mrp.bom.comparison', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Component')
    level = fields.Integer('Level', default=0)
    bom_path = fields.Char('Path')
    qty_a = fields.Float('Qty in A', digits='Product Unit Of Measure')
    qty_b = fields.Float('Qty in B', digits='Product Unit Of Measure')
    qty_diff = fields.Float('Delta', digits='Product Unit Of Measure')
    status = fields.Selection(
        [('same', 'Unchanged'),
         ('added', 'Added'),
         ('removed', 'Removed'),
         ('changed', 'Qty Changed')],
        string='Status')
