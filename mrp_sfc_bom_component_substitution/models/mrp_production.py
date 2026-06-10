# -*- coding: utf-8 -*-

from odoo import fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    substituted_move_count = fields.Integer(
        'Substituted Components', compute='_compute_substituted_move_count')

    def _compute_substituted_move_count(self):
        for production in self:
            production.substituted_move_count = len(
                production.move_raw_ids.filtered('original_product_id'))

    def _component_free_qty(self, product):
        self.ensure_one()
        scoped = product.with_context(
            warehouse=self.warehouse_id.id) if self.warehouse_id else product
        return scoped.free_qty

    def action_substitute_components(self):
        """For each short raw component, swap to the first valid in-stock
        substitute declared on its BoM line."""
        today = fields.Date.today()
        swapped = self.env['stock.move']
        for production in self:
            moves = production.move_raw_ids.filtered(
                lambda m: m.state not in ('done', 'cancel') and m.bom_line_id)
            for move in moves:
                if production._component_free_qty(move.product_id) >= move.product_qty:
                    continue
                for substitute in move.bom_line_id._valid_substitutes(today):
                    candidate = substitute.product_id
                    if production._component_free_qty(candidate) >= move.product_qty:
                        if move._apply_component_substitute(candidate):
                            swapped |= move
                        break
        if not swapped:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Component Substitution'),
                    'message': _('No short component had an available substitute.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Component Substitution'),
                'message': _('%s component(s) substituted.', len(swapped)),
                'type': 'success',
                'sticky': False,
            },
        }
