# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDemand(TransactionCase):

    def test_sales_demand_drives_plan(self):
        wh = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        def product(name):
            return self.env['product.product'].create(
                {'name': name, 'type': 'consu', 'is_storable': True})
        sa, fp = product('DM SA'), product('DM FP')
        self.env['mrp.bom'].create({
            'product_tmpl_id': fp.product_tmpl_id.id, 'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': sa.id, 'product_qty': 2.0})]})
        cust = self.env['res.partner'].create({'name': 'DM Cust'})
        so = self.env['sale.order'].create({
            'partner_id': cust.id,
            'order_line': [(0, 0, {'product_id': fp.id, 'product_uom_qty': 20.0})]})
        so.action_confirm()
        run = self.env['mrp.planning.run'].create({
            'warehouse_id': wh.id, 'include_sales_demand': True, 'multilevel': True})
        run.action_run()
        fp_line = run.line_ids.filtered(lambda l: l.product_id == fp)
        sa_line = run.line_ids.filtered(lambda l: l.product_id == sa)
        self.assertTrue(fp_line)
        self.assertAlmostEqual(fp_line.suggested_qty, 20.0)
        self.assertAlmostEqual(sa_line.suggested_qty, 40.0)  # demand exploded
