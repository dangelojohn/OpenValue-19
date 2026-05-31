# -*- coding: utf-8 -*-

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    # stock_account module: stamp the manufacturing-order reference on the stock
    # valuation journal entry so it surfaces under the MO "Account Moves" button.
    #
    # v19 change (verified against addons/stock_account/models/stock_move.py): the
    # v16 hooks `_prepare_account_move_vals` / `_prepare_account_move_line` no longer
    # exist. The valuation account.move is built inline in `_create_account_move`,
    # which batches the whole recordset into a single move. We therefore post-stamp
    # the created move, and only when the batch maps unambiguously to one MO (mixed
    # batches are left unstamped rather than mislabelled).
    def _create_account_move(self):
        account_move = super()._create_account_move()
        if account_move:
            productions = self.production_id | self.raw_material_production_id
            if len(productions) == 1:
                account_move.manufacture_order_id = productions.id
        return account_move

    # stock_account module: put the production's analytic account on the stock
    # valuation analytic line.
    #
    # v19 change: analytic on a stock move is driven by `_get_analytic_distribution`
    # (a {account_id: percent} dict consumed by `_prepare_analytic_lines` ->
    # `_perform_analytic_distribution`), replacing the v16 `analytic_account_id`
    # assignment on the valuation debit line. We only supply a distribution when the
    # framework hasn't already (so native/account-category distribution wins).
    def _get_analytic_distribution(self):
        distribution = super()._get_analytic_distribution()
        if distribution:
            return distribution
        production = self.production_id or self.raw_material_production_id
        if production.analytic_account_id:
            return {str(production.analytic_account_id.id): 100}
        return distribution
