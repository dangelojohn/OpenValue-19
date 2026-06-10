# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpBomLineSubstitute(models.Model):
    _name = 'mrp.bom.line.substitute'
    _description = 'BoM Component Substitute'
    _order = 'sequence, id'

    bom_line_id = fields.Many2one(
        'mrp.bom.line', 'BoM Line', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one(
        'product.product', 'Substitute Product', required=True)
    sequence = fields.Integer('Priority', default=10)
    date_start = fields.Date('Valid From')
    date_end = fields.Date('Valid To')


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    substitute_ids = fields.One2many(
        'mrp.bom.line.substitute', 'bom_line_id', 'Substitutes')

    def _valid_substitutes(self, on_date):
        """Substitutes valid on ``on_date``, ordered by priority."""
        self.ensure_one()
        valid = self.substitute_ids.filtered(
            lambda s: (not s.date_start or s.date_start <= on_date)
            and (not s.date_end or s.date_end >= on_date))
        return valid.sorted('sequence')
