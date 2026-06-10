# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    is_external = fields.Boolean(
        'External Operation',
        help="This operation is outsourced to a vendor instead of being run "
             "in-house. A purchase order is generated for the service.")
    external_partner_id = fields.Many2one(
        'res.partner', 'Subcontractor',
        domain=[('supplier_rank', '>', 0)])
    external_service_product_id = fields.Many2one(
        'product.product', 'Service Product',
        domain=[('type', '=', 'service')],
        help="The purchased service representing this outsourced operation.")
    external_price = fields.Float(
        'External Unit Price',
        help="Unit price for the outsourced service. If 0, the service "
             "product's cost is used.")
