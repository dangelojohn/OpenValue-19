# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMto(TransactionCase):

    def test_delay_days(self):
        wh = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        comp = self.env['product.product'].create(
            {'name': 'MTO Comp', 'type': 'consu', 'is_storable': True})
        fp = self.env['product.product'].create(
            {'name': 'MTO FP', 'type': 'consu', 'is_storable': True})
        self.env['mrp.bom'].create({
            'product_tmpl_id': fp.product_tmpl_id.id, 'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': comp.id, 'product_qty': 1.0})]})
        self.env['stock.warehouse.orderpoint'].create({
            'product_id': fp.id, 'location_id': wh.lot_stock_id.id,
            'product_min_qty': 10.0, 'product_max_qty': 50.0})
        run = self.env['mrp.planning.run'].create({
            'warehouse_id': wh.id, 'multilevel': False, 'include_sales_demand': False})
        run.action_run()
        line = run.line_ids.filtered(lambda l: l.product_id == fp)
        line.action_release()
        line.generated_ref.date_start = fields.Datetime.now() + timedelta(days=10)
        line.invalidate_recordset(['is_delayed', 'delay_days', 'scheduled_date'])
        self.assertTrue(line.is_delayed)
        self.assertEqual(line.delay_days, 10)
