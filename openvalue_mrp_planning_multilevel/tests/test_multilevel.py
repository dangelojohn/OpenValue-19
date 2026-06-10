# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMultilevel(TransactionCase):

    def test_dependent_demand_cascade(self):
        wh = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        def product(name):
            return self.env['product.product'].create(
                {'name': name, 'type': 'consu', 'is_storable': True})
        raw, sa, fp = product('ML RAW'), product('ML SA'), product('ML FP')
        self.env['mrp.bom'].create({
            'product_tmpl_id': sa.product_tmpl_id.id, 'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': raw.id, 'product_qty': 3.0})]})
        self.env['mrp.bom'].create({
            'product_tmpl_id': fp.product_tmpl_id.id, 'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': sa.id, 'product_qty': 2.0})]})
        self.env['stock.warehouse.orderpoint'].create({
            'product_id': fp.id, 'location_id': wh.lot_stock_id.id,
            'product_min_qty': 10.0, 'product_max_qty': 50.0})
        run = self.env['mrp.planning.run'].create(
            {'warehouse_id': wh.id, 'multilevel': True})
        run.action_run()

        def qty(p):
            line = run.line_ids.filtered(lambda l: l.product_id == p)
            return line.suggested_qty if line else 0.0
        self.assertAlmostEqual(qty(fp), 50.0)
        self.assertAlmostEqual(qty(sa), 100.0)   # 50 x 2
        self.assertAlmostEqual(qty(raw), 300.0)  # 100 x 3
        self.assertEqual(
            run.line_ids.filtered(lambda l: l.product_id == raw).supply_type, 'buy')
