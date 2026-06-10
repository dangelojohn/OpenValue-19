# -*- coding: utf-8 -*-

from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center',
        help="Manufacturing work center this equipment belongs to.")
