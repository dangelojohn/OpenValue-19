# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpAvailabilityLine(models.Model):
    _name = 'mrp.availability.line'
    _description = 'MRP Availability Check Line'
    _order = 'check_type, is_shortage desc, id'

    production_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order', required=True,
        ondelete='cascade', index=True)
    check_type = fields.Selection(
        [('material', 'Material'), ('capacity', 'Capacity')],
        string='Type', required=True)
    is_shortage = fields.Boolean('Is Shortage')

    # Material
    product_id = fields.Many2one('product.product', 'Component')
    product_uom_id = fields.Many2one('uom.uom', 'UoM')
    required_qty = fields.Float('Required', digits='Product Unit Of Measure')
    available_qty = fields.Float('Available', digits='Product Unit Of Measure')
    shortage_qty = fields.Float('Shortage', digits='Product Unit Of Measure')

    # Capacity
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center')
    required_hours = fields.Float('Required (h)')
    available_hours = fields.Float('Available (h)')
    shortage_hours = fields.Float('Shortage (h)')
