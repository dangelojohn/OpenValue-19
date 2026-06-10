# -*- coding: utf-8 -*-

from odoo import fields, models

# Strategies added on top of the native Corrective / Preventive.
MRO_STRATEGIES = [
    ('on_condition', 'On Condition'),
    ('periodic', 'Periodic'),
    ('retrofit', 'Retrofit'),
]


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    maintenance_type = fields.Selection(
        selection_add=MRO_STRATEGIES,
        ondelete={k: 'set default' for k, _v in MRO_STRATEGIES})
