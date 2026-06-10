# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPlanningEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1)

    def _product(self, name, **kw):
        vals = {'name': name, 'type': 'consu', 'is_storable': True}
        vals.update(kw)
        return self.env['product.product'].create(vals)

    def _orderpoint(self, product, mn, mx):
        return self.env['stock.warehouse.orderpoint'].create({
            'product_id': product.id, 'location_id': self.wh.lot_stock_id.id,
            'product_min_qty': mn, 'product_max_qty': mx})

    def test_reorder_proposes_manufacture(self):
        comp = self._product('PE Comp')
        fp = self._product('PE FP')
        self.env['mrp.bom'].create({
            'product_tmpl_id': fp.product_tmpl_id.id, 'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': comp.id, 'product_qty': 1.0})]})
        self._orderpoint(fp, 10.0, 50.0)
        run = self.env['mrp.planning.run'].create({'warehouse_id': self.wh.id})
        run.action_run()
        line = run.line_ids.filtered(lambda l: l.product_id == fp)
        self.assertTrue(line, "a planning line should be proposed for FP")
        self.assertEqual(run.state, 'done')
        self.assertAlmostEqual(line.suggested_qty, 50.0)
        self.assertEqual(line.supply_type, 'manufacture')

    def test_release_creates_manufacturing_order(self):
        comp = self._product('PE Comp2')
        fp = self._product('PE FP2')
        self.env['mrp.bom'].create({
            'product_tmpl_id': fp.product_tmpl_id.id, 'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': comp.id, 'product_qty': 1.0})]})
        self._orderpoint(fp, 5.0, 20.0)
        run = self.env['mrp.planning.run'].create({'warehouse_id': self.wh.id})
        run.action_run()
        line = run.line_ids.filtered(lambda l: l.product_id == fp)
        line.action_release()
        self.assertTrue(line.released)
        self.assertEqual(line.generated_ref._name, 'mrp.production')
        self.assertAlmostEqual(line.generated_ref.product_qty, 20.0)
