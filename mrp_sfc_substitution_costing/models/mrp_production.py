# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    substitution_cost_delta = fields.Float(
        'Substitution Cost Impact', digits='Product Price',
        compute='_compute_substitution_cost_delta', store=True,
        help="Material-cost difference introduced by component substitutions "
             "(substitute standard price minus original, times quantity). "
             "This is the portion of the material variance due to substitution.")

    @api.depends('move_raw_ids.original_product_id',
                 'move_raw_ids.product_id',
                 'move_raw_ids.product_qty',
                 'move_raw_ids.state')
    def _compute_substitution_cost_delta(self):
        for production in self:
            delta = 0.0
            substituted = production.move_raw_ids.filtered(
                lambda m: m.original_product_id and m.state != 'cancel')
            for move in substituted:
                delta += (move.product_id.standard_price
                          - move.original_product_id.standard_price) * move.product_qty
            production.substitution_cost_delta = delta
