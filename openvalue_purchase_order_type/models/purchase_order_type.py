# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseOrderType(models.Model):
    _name = 'purchase.order.type'
    _description = 'Purchase Order Type'
    _order = 'sequence, name'

    name = fields.Char('Type', required=True, translate=True)
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company)
