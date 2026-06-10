# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCapacity(TransactionCase):

    def test_overload_flagged(self):
        company = self.env.company
        wh = self.env['stock.warehouse'].search(
            [('company_id', '=', company.id)], limit=1)
        wc = self.env['mrp.workcenter'].create(
            {'name': 'CAP WC', 'resource_calendar_id': company.resource_calendar_id.id})
        products = []
        for i in range(2):
            comp = self.env['product.product'].create(
                {'name': 'CAP C%s' % i, 'type': 'consu', 'is_storable': True})
            fp = self.env['product.product'].create(
                {'name': 'CAP F%s' % i, 'type': 'consu', 'is_storable': True})
            self.env['mrp.bom'].create({
                'product_tmpl_id': fp.product_tmpl_id.id, 'product_qty': 1.0,
                'bom_line_ids': [(0, 0, {'product_id': comp.id, 'product_qty': 1.0})],
                'operation_ids': [(0, 0, {
                    'name': 'Op', 'workcenter_id': wc.id,
                    'time_cycle_manual': 60.0, 'sequence': 10})]})
            self.env['stock.warehouse.orderpoint'].create({
                'product_id': fp.id, 'location_id': wh.lot_stock_id.id,
                'product_min_qty': 1.0, 'product_max_qty': 30.0})
            products.append(fp)
        run = self.env['mrp.planning.run'].create({
            'warehouse_id': wh.id, 'capacity_horizon_days': 7,
            'multilevel': False, 'include_sales_demand': False})
        run.action_run()
        lines = run.line_ids.filtered(lambda l: l.product_id in products)
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertAlmostEqual(line.required_hours, 30.0)
            self.assertTrue(line.capacity_overloaded)  # 2 x 30h > ~40h / 7 days
        self.assertEqual(run.overloaded_workcenter_count, 1)
