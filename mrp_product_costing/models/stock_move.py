# -*- coding: utf-8 -*-

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _mo_for_valuation(self):
        """The manufacturing order a valuation move belongs to (finished or raw)."""
        self.ensure_one()
        return self.production_id or self.raw_material_production_id

    def _create_account_move(self):
        """Stamp the manufacturing order onto the generated valuation entry.

        Odoo 19 rebuilt stock valuation: the old ``_prepare_account_move_vals``
        / ``_prepare_account_move_line`` hooks are gone, replaced by
        ``_create_account_move`` (header) and ``_get_account_move_line_vals``.
        """
        account_move = super()._create_account_move()
        if account_move:
            mo = self.filtered(lambda m: m._mo_for_valuation())[:1]
            if mo:
                account_move.manufacture_order_id = mo._mo_for_valuation().id
        return account_move

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        """Tag valuation analytic lines with the manufacturing order.

        The legacy single ``analytic_account_id`` assignment is dropped: in v19
        the analytic account flows through ``analytic_distribution`` natively.
        We only add the MO back-reference and category here.
        """
        vals = super()._prepare_analytic_line_values(account_field_values, amount, unit_amount)
        mo = self._mo_for_valuation()
        if mo:
            vals['manufacture_order_id'] = mo.id
            vals['category'] = 'manufacturing_order'
        return vals
