# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    original_product_id = fields.Many2one(
        'product.product', 'Substituted From', copy=False,
        help="Original component this move was substituted away from.")

    def _apply_component_substitute(self, new_product):
        """Swap this raw move to a substitute product, keeping the link to the
        BoM line and recording the original component."""
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            return False
        self._do_unreserve()
        if not self.original_product_id:
            self.original_product_id = self.product_id.id
        self.write({
            'product_id': new_product.id,
            'product_uom': new_product.uom_id.id,
        })
        self._action_assign()
        return True
