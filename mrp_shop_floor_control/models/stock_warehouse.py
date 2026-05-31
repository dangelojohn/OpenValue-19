# -*- coding: utf-8 -*-

from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    calendar_id = fields.Many2one(
        'resource.calendar', 'Working Calendar',
        help="Calendar used by Shop Floor Control to plan release and floating "
             "times around manufacturing for this warehouse.")
