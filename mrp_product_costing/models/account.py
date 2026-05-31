# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    manufacture_order_id = fields.Many2one(
        "mrp.production", "Manufacturing Order", copy=False, index=True, readonly=True)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # account module: propagate the manufacturing order reference from the journal
    # item to the analytic line(s).
    #
    # v19 change (verified against addons/account/models/account_move_line.py):
    #   - the v16 singular `_prepare_analytic_line` and public `create_analytic_lines`
    #     are gone. `_create_analytic_lines` (private) now calls the *plural*
    #     `_prepare_analytic_lines`, which is `ensure_one()` and returns a LIST of
    #     vals dicts (one analytic line per analytic account in the distribution).
    #   - the analytic line links back via `move_line_id`, not the old `move_id`.
    # Overriding the plural prep method stamps the MO reference + category on every
    # dict produced for this line, and is naturally correct for multi-line moves
    # (each move line resolves its own move's MO). This is the binding point whose
    # failure is SILENT: postings still balance, but the MO back-reference is lost.
    def _prepare_analytic_lines(self):
        analytic_line_vals = super()._prepare_analytic_lines()
        if self.move_id.manufacture_order_id:
            for vals in analytic_line_vals:
                vals.update({
                    'manufacture_order_id': self.move_id.manufacture_order_id.id,
                    'category': 'manufacturing_order',
                })
        return analytic_line_vals


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    # The journal-item link (`move_line_id`) is provided natively in v19; the v16
    # custom `move_id` Many2one is dropped. Only the MO back-reference is added.
    manufacture_order_id = fields.Many2one(
        "mrp.production", "Manufacturing Order", copy=False, index=True, readonly=True)
