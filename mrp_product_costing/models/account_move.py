# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    manufacture_order_id = fields.Many2one(
        "mrp.production", "Manufacturing Order", copy=False, index=True, readonly=True)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_analytic_lines(self):
        """Stamp the originating manufacturing order on each analytic line.

        Odoo 19 renamed the prep hook to the plural ``_prepare_analytic_lines``
        (the singular pre-distribution method is gone) and it returns one vals
        dict *per analytic account* in the distribution.  We stamp every dict.
        """
        vals_list = super()._prepare_analytic_lines()
        mo = self.move_id.manufacture_order_id
        if mo:
            for vals in vals_list:
                vals['manufacture_order_id'] = mo.id
                vals['category'] = 'manufacturing_order'
        return vals_list


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    manufacture_order_id = fields.Many2one(
        "mrp.production", "Manufacturing Order", copy=False, index=True, readonly=True)
    # Odoo 19's base category selection is only [('other', 'Other')]; extend it
    # so analytic lines produced by this module are filterable/reportable.
    category = fields.Selection(
        selection_add=[('manufacturing_order', 'Manufacturing Order')],
        ondelete={'manufacturing_order': 'set default'})
