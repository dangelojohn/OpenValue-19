# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MrpCapacityCheck(models.TransientModel):
    _name = 'mrp.capacity.check'
    _description = 'MRP Capacity Check'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', readonly=True)
    capacity_item_ids = fields.One2many(
        'mrp.capacity.check.item', 'check_id', string="Capacity Items", readonly=True)

    def _populate(self):
        """Build the capacity-check lines from the SFC capacity-load records.
        Called explicitly (from the production action) rather than from an
        onchange, so it can safely create records."""
        self.ensure_one()
        self.capacity_item_ids.unlink()
        Load = self.env['mrp.workcenter.load']
        workcenters = self.production_id.workorder_ids.workcenter_id

        # Requirements of THIS manufacturing order, per work center and week.
        mo_groups = Load._read_group(
            [('production_id', '=', self.production_id.id)],
            ['workcenter_id', 'week_nro'],
            ['wo_capacity_requirements:sum'])

        Item = self.env['mrp.capacity.check.item']
        items = self.env['mrp.capacity.check.item']
        weeks = set()
        for workcenter, week, requirements in mo_groups:
            if not week:
                continue
            weeks.add(week)
            items |= Item.create({
                'check_id': self.id,
                'workcenter_id': workcenter.id,
                'week_nro': week,
                'wo_capacity_requirements': requirements,
            })

        if not weeks:
            return

        # Total requirements across ALL manufacturing orders, per WC and week.
        all_groups = Load._read_group(
            [('workcenter_id', 'in', workcenters.ids), ('week_nro', 'in', list(weeks))],
            ['workcenter_id', 'week_nro'],
            ['wo_capacity_requirements:sum'])
        totals = {(wc.id, week): value for wc, week, value in all_groups}
        for item in items:
            item.all_wo_capacity_requirements = totals.get(
                (item.workcenter_id.id, item.week_nro), 0.0)


class MrpCapacityCheckItem(models.TransientModel):
    _name = 'mrp.capacity.check.item'
    _description = 'MRP Capacity Check Item'

    check_id = fields.Many2one('mrp.capacity.check', readonly=True, ondelete='cascade')
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center')
    week_nro = fields.Char('Week Number')
    wo_capacity_requirements = fields.Float('WO Capacity Requirements (Hours)')
    wc_available_capacity = fields.Float(
        'WC Weekly Available Capacity', compute='_compute_available_capacity')
    all_wo_capacity_requirements = fields.Float('All WO Capacity Requirements (Hours)')
    wc_capacity_load = fields.Float('WC Capacity Load %', compute='_compute_capacity_load')
    wc_remaining_capacity = fields.Float('WC Remaining Capacity', compute='_compute_capacity_load')

    @api.depends('week_nro', 'workcenter_id')
    def _compute_available_capacity(self):
        Load = self.env['mrp.workcenter.load']
        for item in self:
            load = Load.search([
                ('workcenter_id', '=', item.workcenter_id.id),
                ('week_nro', '=', item.week_nro),
            ], limit=1)
            item.wc_available_capacity = load.wc_available_capacity

    @api.depends('all_wo_capacity_requirements', 'wc_available_capacity')
    def _compute_capacity_load(self):
        for item in self:
            if item.wc_available_capacity:
                item.wc_capacity_load = (
                    item.all_wo_capacity_requirements / item.wc_available_capacity) * 100.0
            else:
                item.wc_capacity_load = 0.0
            item.wc_remaining_capacity = (
                item.wc_available_capacity - item.all_wo_capacity_requirements)

    def open_pivot_info(self):
        self.ensure_one()
        return {
            'name': _("Work Center Capacity Load"),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workcenter.load',
            'view_mode': 'pivot,graph,list',
            'domain': [('workcenter_id', '=', self.workcenter_id.id)],
            'context': {'default_workcenter_id': self.workcenter_id.id},
            'target': 'current',
        }
