# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpFloatingTimes(models.Model):
    _name = 'mrp.floating.times'
    _description = 'MRP Floating Times'

    # NB: stock.warehouse.manufacture_to_resupply is a non-stored computed field
    # in Odoo 19, so it cannot be used in a (SQL) domain here.
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company', related='warehouse_id.company_id',
        store=True, readonly=True)
    mrp_release_time = fields.Float("Release Time (Hours)", default=1.0)
    mrp_ftbp_time = fields.Float("Floating Time Before Production (Hours)", default=1.0)
    mrp_ftap_time = fields.Float("Floating Time After Production (Hours)", default=1.0)

    _sql_constraints = [
        ('warehouse_uniq', 'unique(warehouse_id)',
         'A Floating Times record already exists for this warehouse.'),
    ]

    @api.model
    def create_floating_times(self):
        """Create a default Floating Times record for every manufacturing
        warehouse that does not have one yet (idempotent)."""
        warehouses = self.env['stock.warehouse'].with_context(active_test=False).search(
            []).filtered('manufacture_to_resupply')
        existing = set(self.search([]).mapped('warehouse_id').ids)
        vals = [{
            'warehouse_id': warehouse.id,
            'mrp_release_time': 1.0,
            'mrp_ftbp_time': 1.0,
            'mrp_ftap_time': 1.0,
        } for warehouse in warehouses if warehouse.id not in existing]
        if vals:
            self.create(vals)
        return True

    @api.model
    def _get_for_warehouse(self, warehouse):
        record = self.search([('warehouse_id', '=', warehouse.id)], limit=1)
        if not record:
            raise UserError(_(
                'No Floating Times record has been configured for the '
                'warehouse: %s', warehouse.display_name or warehouse.name))
        return record
