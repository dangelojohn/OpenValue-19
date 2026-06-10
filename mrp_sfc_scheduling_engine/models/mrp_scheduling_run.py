# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Sentinel deadline for work orders whose manufacturing order has no deadline,
# so the EDD rule keeps them last without special-casing None comparisons.
_FAR_FUTURE = datetime(2099, 1, 1)


class MrpSchedulingRun(models.Model):
    _name = 'mrp.scheduling.run'
    _description = 'SFC Scheduling Engine Run'
    _order = 'create_date desc'

    name = fields.Char('Reference', default=lambda self: _('New'), copy=False)
    objective = fields.Selection(
        [
            ('makespan', 'Makespan'),
            ('tardiness', 'Tardiness'),
            ('sum_completion', 'Sum Completion'),
            ('wip', 'Length / WIP'),
        ],
        string='Objective Function', required=True, default='tardiness',
        help="Dispatching rule used by the optimizer:\n"
             "- Makespan: minimise time to finish all orders (longest first)\n"
             "- Tardiness: minimise lateness vs deadlines (earliest due first)\n"
             "- Sum Completion: minimise total completion time (shortest first)\n"
             "- Length / WIP: minimise flow time (release order)")
    date_start = fields.Datetime(
        'Horizon Start', default=fields.Datetime.now, required=True,
        help="No work order is scheduled to start before this moment.")
    production_ids = fields.Many2many(
        'mrp.production', string='Manufacturing Orders',
        help="Restrict scheduling to these orders. Leave empty to schedule "
             "every open work order.")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env.company)
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Scheduled')],
        default='draft', required=True, copy=False)

    line_ids = fields.One2many(
        'mrp.scheduling.run.line', 'run_id', 'Scheduled Work Orders', copy=False)
    workorder_count = fields.Integer('Work Orders', compute='_compute_counts')

    # KPIs (hours)
    makespan_hours = fields.Float('Makespan (h)', readonly=True, copy=False)
    sum_completion_hours = fields.Float('Sum Completion (h)', readonly=True, copy=False)
    total_tardiness_hours = fields.Float('Total Tardiness (h)', readonly=True, copy=False)
    avg_wip = fields.Float('Avg WIP', readonly=True, copy=False)

    @api.depends('line_ids')
    def _compute_counts(self):
        for run in self:
            run.workorder_count = len(run.line_ids)

    # ------------------------------------------------------------------ helpers
    def _get_schedulable_workorders(self):
        """Open work orders (not yet started / done / cancelled) in scope."""
        self.ensure_one()
        domain = [
            ('state', 'in', ('blocked', 'ready')),
            ('company_id', '=', self.company_id.id),
        ]
        if self.production_ids:
            domain.append(('production_id', 'in', self.production_ids.ids))
        return self.env['mrp.workorder'].search(domain)

    def _priority_key(self, op):
        """Dispatching priority — lower sorts first (higher priority)."""
        objective = self.objective
        if objective == 'tardiness':
            return (op['due'], op['dur'])            # EDD, tie-break shortest
        if objective == 'sum_completion':
            return (op['dur'], op['due'])            # SPT
        if objective == 'makespan':
            return (-op['dur'], op['due'])           # LPT
        return (op['release'], op['seq'])            # WIP: release FIFO

    # -------------------------------------------------------------------- engine
    def action_run(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_(
                "This scheduling run has already been executed. Create a new "
                "run to re-optimise."))
        workorders = self._get_schedulable_workorders()
        if not workorders:
            raise UserError(_("No open work orders found to schedule."))

        horizon = self.date_start or fields.Datetime.now()

        # Build the operation set.
        ops = {}
        for wo in workorders:
            if not wo.workcenter_id:
                continue
            mo = wo.production_id
            ops[wo.id] = {
                'wo': wo,
                'mo': mo.id,
                'seq': wo.sfc_sequence,
                'wc': wo.workcenter_id,
                'dur': (wo.duration_expected or 0.0) / 60.0,
                'due': mo.date_deadline or _FAR_FUTURE,
                'release': mo.date_planned_start_wo or mo.date_start or horizon,
                'start': None,
                'finish': None,
            }
        if not ops:
            raise UserError(_("Work orders found, but none have a work center."))

        # Precedence: within an MO, an op waits for every lower-sfc_sequence op.
        by_mo = defaultdict(list)
        for oid, op in ops.items():
            by_mo[op['mo']].append(oid)
        preds = {
            oid: [p for p in by_mo[op['mo']] if ops[p]['seq'] < op['seq']]
            for oid, op in ops.items()
        }

        # Finite-capacity resource timelines: one "free-at" cursor per slot.
        slots = {}

        def wc_slots(wc):
            if wc.id not in slots:
                capacity = max(1, int(round(wc._sfc_capacity() or 1.0)))
                slots[wc.id] = [horizon] * capacity
            return slots[wc.id]

        # List scheduling: repeatedly dispatch the highest-priority ready op.
        scheduled = set()
        remaining = set(ops)
        guard = 0
        max_iter = len(ops) + 5
        while remaining and guard < max_iter:
            guard += 1
            ready = [oid for oid in remaining
                     if all(p in scheduled for p in preds[oid])]
            if not ready:
                break  # safety: should not happen with acyclic sfc_sequence
            oid = min(ready, key=lambda i: self._priority_key(ops[i]))
            op = ops[oid]
            pred_finish = max(
                [ops[p]['finish'] for p in preds[oid]], default=horizon)
            cursors = wc_slots(op['wc'])
            idx = min(range(len(cursors)), key=lambda i: cursors[i])
            start = max(cursors[idx], pred_finish, horizon)
            calendar = op['wc'].resource_calendar_id
            if calendar:
                start = calendar.plan_hours(0.0, start, compute_leaves=True)
                finish = calendar.plan_hours(
                    op['dur'], start, compute_leaves=True) if op['dur'] else start
            else:
                finish = start + timedelta(hours=op['dur'])
            op['start'], op['finish'] = start, finish
            cursors[idx] = finish
            scheduled.add(oid)
            remaining.discard(oid)

        if remaining:
            raise UserError(_(
                "Could not schedule all work orders (possible precedence "
                "cycle in SFC sequences). %s left unscheduled.") % len(remaining))

        self._apply_schedule(ops, horizon)
        return True

    def _apply_schedule(self, ops, horizon):
        """Write the computed schedule back to the SFC planning layer, rebuild
        the capacity load, snapshot result lines, and compute KPIs."""
        self.ensure_one()
        Line = self.env['mrp.scheduling.run.line']
        affected = self.env['mrp.workorder']
        mo_bounds = {}
        self.line_ids.unlink()
        line_vals = []
        for op in ops.values():
            if not op['start'] or not op['finish']:
                continue
            wo = op['wo']
            wo.write({
                'date_planned_start_wo': op['start'],
                'date_planned_finished_wo': op['finish'],
            })
            affected |= wo
            lo, hi = mo_bounds.get(op['mo'], (op['start'], op['finish']))
            mo_bounds[op['mo']] = (min(lo, op['start']), max(hi, op['finish']))
            tardy = 0.0
            if op['due'] != _FAR_FUTURE and op['finish'] > op['due']:
                tardy = (op['finish'] - op['due']).total_seconds() / 3600.0
            line_vals.append({
                'run_id': self.id,
                'workorder_id': wo.id,
                'sfc_sequence': op['seq'],
                'date_planned_start_wo': op['start'],
                'date_planned_finished_wo': op['finish'],
                'duration_hours': op['dur'],
                'tardiness_hours': tardy,
            })
        Line.create(line_vals)

        # Rebuild the daily capacity-load rows via the base SFC method.
        affected._rebuild_capacity_load()
        for mo_id, (lo, hi) in mo_bounds.items():
            self.env['mrp.production'].browse(mo_id).write({
                'date_planned_start_wo': lo,
                'date_planned_finished_wo': hi,
            })

        # KPIs.
        finishes = [op['finish'] for op in ops.values() if op['finish']]
        makespan = (max(finishes) - horizon).total_seconds() / 3600.0 if finishes else 0.0
        mo_finish = {}
        for op in ops.values():
            if op['finish']:
                mo_finish[op['mo']] = max(
                    mo_finish.get(op['mo'], op['finish']), op['finish'])
        sum_completion = sum(
            (f - horizon).total_seconds() / 3600.0 for f in mo_finish.values())
        total_tardiness = 0.0
        for mo_id, f in mo_finish.items():
            due = self.env['mrp.production'].browse(mo_id).date_deadline
            if due and f > due:
                total_tardiness += (f - due).total_seconds() / 3600.0
        self.write({
            'makespan_hours': makespan,
            'sum_completion_hours': sum_completion,
            'total_tardiness_hours': total_tardiness,
            'avg_wip': (sum_completion / makespan) if makespan else 0.0,
            'state': 'done',
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'mrp.scheduling.run') or _('New')
        return super().create(vals_list)

    def action_view_workorders(self):
        self.ensure_one()
        return {
            'name': _('Scheduled Work Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.line_ids.workorder_id.ids)],
        }


class MrpSchedulingRunLine(models.Model):
    _name = 'mrp.scheduling.run.line'
    _description = 'SFC Scheduling Engine Run Line'
    _order = 'date_planned_start_wo, id'

    run_id = fields.Many2one(
        'mrp.scheduling.run', 'Scheduling Run', required=True,
        ondelete='cascade', index=True)
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order', required=True, ondelete='cascade')
    production_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order',
        related='workorder_id.production_id', store=True)
    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center',
        related='workorder_id.workcenter_id', store=True)
    sfc_sequence = fields.Integer('SFC Sequence')
    date_planned_start_wo = fields.Datetime('Scheduled Start')
    date_planned_finished_wo = fields.Datetime('Scheduled End')
    duration_hours = fields.Float('Duration (h)')
    tardiness_hours = fields.Float('Tardiness (h)')
