# -*- coding: utf-8 -*-

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    # stock_account module: preparazione dei dati di testata per la generazione del movimento contabile a partire dal movimento di magazzino
    # valorizzazione del riferimento al manufacturing order
    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        vals = super()._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        if self.production_id:
            vals['manufacture_order_id'] = self.production_id.id
        elif self.raw_material_production_id:
            vals['manufacture_order_id'] = self.raw_material_production_id.id
        return vals

    # stock_account module: preparazione dei dati di riga per la generazione del movimento contabile a partire dal movimento di magazzino
    # valorizzazione dell'analytic account
    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, description):
        res = super()._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
        analytic_account = self.production_id.analytic_account_id.id or self.raw_material_production_id.analytic_account_id.id
        #manufacture_order_id = self.production_id.id or self.raw_material_production_id.id
        for line in res:
            #if manufacture_order_id:
                #line[2]["manufacture_order_id"] = manufacture_order_id
            if analytic_account:
                if line[2]["account_id"] != self.product_id.categ_id.property_stock_valuation_account_id.id:
                    line[2]["analytic_account_id"] = analytic_account
        return res

    # mrp_account module: valorizzare nella scrittura analitica il riferimento al manufacturing order
    def _generate_analytic_lines_data(self, unit_amount, amount):
        vals = super()._generate_analytic_lines_data(unit_amount, amount)
        if self.raw_material_production_id.analytic_account_id:
            vals['manufacture_order_id'] = self.raw_material_production_id.id
        return vals
