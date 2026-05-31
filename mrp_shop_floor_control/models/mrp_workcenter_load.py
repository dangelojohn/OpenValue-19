# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import api, fields, models


class MrpWorkcenterLoad(models.Model):
    """Shop Floor Control capacity load.

    This is an analytical, module-owned table (one row per work order and per
    calendar day it spans).  It is intentionally a *new* model and does NOT
    inherit Odoo's core ``mrp.workcenter.capacity`` (which stores per-product
    work-center capacities), to avoid polluting standard capacity look-ups.
    """
    _name = 'mrp.workcenter.load'
    _description = 'Work Center Capacity Load'
    _order = 'date_planned desc'

    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', required=True, index=True, ondelete='cascade')
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order', required=True, index=True, ondelete='cascade')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', related='workorder_id.production_id', store=True)
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float('Required Quantity')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    date_planned = fields.Datetime('Planned Date', default=fields.Datetime.now)
    week_nro = fields.Char('Week Number', compute='_compute_week_number', store=True)
    active = fields.Boolean(default=True)
    wo_capacity_requirements = fields.Float('WO Capacity Requirements')
    wc_available_capacity = fields.Float(
        'WC Weekly Available Capacity', compute='_compute_available_capacity',
        store=True, aggregator='avg')
    wc_daily_available_capacity = fields.Float(
        'WC Daily Available Capacity', compute='_compute_available_capacity',
        store=True, aggregator='avg')

    @api.depends('date_planned')
    def _compute_week_number(self):
        """ISO-8601 week key: ``<ISO year>-<ISO week>`` (e.g. ``2026-22``)."""
        for record in self:
            if record.date_planned:
                iso = record.date_planned.date().isocalendar()
                record.week_nro = '%04d-%02d' % (iso[0], iso[1])
            else:
                record.week_nro = False

    @api.depends('week_nro', 'date_planned', 'workcenter_id')
    def _compute_available_capacity(self):
        for record in self:
            calendar = record.workcenter_id.resource_calendar_id
            wc = record.workcenter_id
            if not calendar or not record.week_nro or not record.date_planned:
                record.wc_available_capacity = 0.0
                record.wc_daily_available_capacity = 0.0
                continue
            # Round-trip the ISO week key with matching ISO directives.
            monday = datetime.strptime(record.week_nro + '-1', "%G-%V-%u")
            sunday = monday + timedelta(days=7)
            hours_week = calendar.get_work_hours_count(monday, sunday)
            capacity = wc._sfc_capacity(record.product_id)
            record.wc_available_capacity = (
                hours_week * capacity * wc.time_efficiency / 100.0)
            day_start = datetime.combine(record.date_planned.date(), datetime.min.time())
            day_end = day_start + timedelta(days=1)
            hours_day = calendar.get_work_hours_count(day_start, day_end)
            record.wc_daily_available_capacity = (
                hours_day * capacity * wc.time_efficiency / 100.0)
