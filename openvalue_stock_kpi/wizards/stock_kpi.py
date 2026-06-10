# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockKpi(models.TransientModel):
    _name = 'stock.kpi'
    _description = 'Stock KPI Dashboard'

    total_onhand_value = fields.Float('Total On-hand Value', readonly=True, digits='Product Price')
    product_in_stock = fields.Integer('Products in Stock', readonly=True)
    product_negative_forecast = fields.Integer('Negative Forecast', readonly=True)

    @api.model
    def _compute_kpis(self):
        storable = self.env['product.product'].search([('is_storable', '=', True)])
        return {
            'total_onhand_value': sum(
                p.qty_available * p.standard_price for p in storable),
            'product_in_stock': len(storable.filtered(lambda p: p.qty_available > 0)),
            'product_negative_forecast': len(
                storable.filtered(lambda p: p.virtual_available < 0)),
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.update(self._compute_kpis())
        return res
