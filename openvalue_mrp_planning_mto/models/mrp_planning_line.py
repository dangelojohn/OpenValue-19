# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpPlanningLine(models.Model):
    _inherit = 'mrp.planning.line'

    scheduled_date = fields.Date(
        'Scheduled Date', compute='_compute_mto_status',
        help="Scheduled date of the generated manufacturing / purchase order.")
    is_delayed = fields.Boolean(
        'Delayed', compute='_compute_mto_status',
        help="The generated order is scheduled later than the planned need date.")
    delay_days = fields.Integer(
        'Delay (days)', compute='_compute_mto_status',
        help="Number of days the generated order is late versus the need date.")

    @api.depends('released', 'planned_date')
    def _compute_mto_status(self):
        for line in self:
            scheduled = False
            ref = line.generated_ref
            if ref:
                if ref._name == 'mrp.production' and ref.date_start:
                    scheduled = ref.date_start.date()
                elif ref._name == 'purchase.order' and ref.date_planned:
                    scheduled = ref.date_planned.date()
            line.scheduled_date = scheduled
            late = bool(scheduled and line.planned_date and scheduled > line.planned_date)
            line.is_delayed = late
            line.delay_days = (scheduled - line.planned_date).days if late else 0
