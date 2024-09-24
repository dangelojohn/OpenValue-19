# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'


    WORKCENTER_TYPE = [
        ('H', 'Man'),
        ('M', 'Machine'),
    ]

    wc_type = fields.Selection(WORKCENTER_TYPE, 'Work Center Type')
    costs_hour = fields.Float('Hourly Variable Cost Rate', default="0.0")
    costs_hour_fixed = fields.Float('Hourly Fixed Direct Cost Rate', default="0.0")
    analytic_account_id = fields.Many2one('account.analytic.account', "Analytic Account")
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
    
    # overheads
    costs_overhead_variable_percentage = fields.Float('Variable OVH Costs percentage', default="0.0")
    costs_overhead_fixed_percentage = fields.Float('Fixed OVH Costs percentage', default="0.0")
    capacity = fields.Float('Capacity', default=1.0) 


