# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    manufacture_order_id = fields.Many2one("mrp.production", "Manufacturing Order", copy=False, index=True, readonly=True)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # account module: propagare il riferimento del manufacturing order della riga del movimento contabile alle scritture analitiche
    def _prepare_analytic_line(self):
        result = super()._prepare_analytic_line()
        for line in self:
            if line.move_id.manufacture_order_id:
                result[0].update({'manufacture_order_id': line.move_id.manufacture_order_id.id, 'category': 'manufacturing_order'})
        return result

    def create_analytic_lines(self):
        super().create_analytic_lines()
        for line in self:
            if line.move_id.manufacture_order_id:
                for analytic_line in line.analytic_line_ids:
                    analytic_line.manufacture_order_id = line.move_id.manufacture_order_id.id
                    analytic_line.category = 'manufacturing_order'


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    move_id = fields.Many2one('account.move.line', string='Journal Item', ondelete='cascade', index=True, check_company=True)
    manufacture_order_id = fields.Many2one("mrp.production", "Manufacturing Order", copy=False, index=True, readonly=True)
