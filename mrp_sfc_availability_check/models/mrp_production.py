# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    availability_state = fields.Selection(
        [('unknown', 'Not Checked'),
         ('available', 'Available'),
         ('shortage', 'Shortage')],
        string='Availability', default='unknown', copy=False, index=True,
        help="Result of the last material + capacity availability check.")
    availability_check_date = fields.Datetime('Last Availability Check', copy=False)
    material_available = fields.Boolean('Material Available', copy=False)
    capacity_available = fields.Boolean('Capacity Available', copy=False)
    availability_line_ids = fields.One2many(
        'mrp.availability.line', 'production_id', 'Availability Lines', copy=False)

    # ------------------------------------------------------------------ material
    def _check_material_availability(self):
        """Explode the BoM (all levels, kits expanded) and compare each leaf
        component's requirement against free stock. Returns a list of line
        vals and a bool 'all available'."""
        self.ensure_one()
        vals = []
        if not self.bom_id:
            return vals, True
        warehouse = self.warehouse_id
        _boms, lines = self.bom_id.explode(
            self.product_id, self.product_uom_qty or self.product_qty)
        required = defaultdict(float)
        product_by_id = {}
        for bom_line, data in lines:
            # data['product'] is the PARENT product of the BoM level (variant
            # context); the actual component is the bom line's product.
            component = bom_line.product_id
            required[component.id] += data['qty']
            product_by_id[component.id] = component
        all_ok = True
        for product_id, req in required.items():
            product = product_by_id[product_id]
            prod = product.with_context(warehouse=warehouse.id) if warehouse else product
            available = prod.free_qty
            shortage = max(0.0, req - available)
            is_short = shortage > 0.0
            if is_short:
                all_ok = False
            vals.append({
                'production_id': self.id,
                'check_type': 'material',
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'required_qty': req,
                'available_qty': available,
                'shortage_qty': shortage,
                'is_shortage': is_short,
            })
        return vals, all_ok

    # ------------------------------------------------------------------ capacity
    def _availability_window(self):
        self.ensure_one()
        start = self.date_start or fields.Datetime.now()
        end = self.date_deadline or (start + timedelta(days=7))
        if end <= start:
            end = start + timedelta(days=7)
        return start, end

    def _check_capacity_availability(self):
        """Sum routing-operation hours per work center and compare with the
        remaining finite capacity in the order window."""
        self.ensure_one()
        vals = []
        if not self.bom_id:
            return vals, True
        start, end = self._availability_window()
        required = defaultdict(float)
        for operation in self.bom_id.operation_ids:
            wc = operation.workcenter_id
            if not wc:
                continue
            minutes = (operation.time_cycle_manual or 0.0) * (self.product_qty or 1.0)
            required[wc] += minutes / 60.0
        Load = self.env['mrp.workcenter.load']
        all_ok = True
        for wc, req_hours in required.items():
            calendar = wc.resource_calendar_id
            if calendar:
                gross = calendar.get_work_hours_count(start, end)
            else:
                gross = (end - start).total_seconds() / 3600.0
            available = gross * wc._sfc_capacity() * (wc.time_efficiency or 100.0) / 100.0
            planned = sum(Load.search([
                ('workcenter_id', '=', wc.id),
                ('date_planned', '>=', start),
                ('date_planned', '<', end),
                ('production_id', '!=', self.id),
            ]).mapped('wo_capacity_requirements'))
            remaining = available - planned
            shortage = max(0.0, req_hours - remaining)
            is_short = shortage > 0.0
            if is_short:
                all_ok = False
            vals.append({
                'production_id': self.id,
                'check_type': 'capacity',
                'workcenter_id': wc.id,
                'required_hours': req_hours,
                'available_hours': remaining,
                'shortage_hours': shortage,
                'is_shortage': is_short,
            })
        return vals, all_ok

    # -------------------------------------------------------------------- action
    def action_check_availability(self):
        Line = self.env['mrp.availability.line']
        for production in self:
            if not production.bom_id:
                raise UserError(_(
                    "%s has no Bill of Materials to check.", production.display_name))
            production.availability_line_ids.unlink()
            mat_vals, mat_ok = production._check_material_availability()
            cap_vals, cap_ok = production._check_capacity_availability()
            Line.create(mat_vals + cap_vals)
            production.write({
                'material_available': mat_ok,
                'capacity_available': cap_ok,
                'availability_state': 'available' if (mat_ok and cap_ok) else 'shortage',
                'availability_check_date': fields.Datetime.now(),
            })
        return True

    @api.model
    def check_availability_for_range(self, date_from, date_to, states=None):
        """Batch-check every order whose planned start falls in a window.
        Used by the Master Production Plan wizard."""
        domain = [
            ('state', 'not in', ('done', 'cancel')),
            ('date_start', '>=', date_from),
            ('date_start', '<=', date_to),
        ]
        if states:
            domain.append(('state', 'in', states))
        orders = self.search(domain)
        orders.filtered('bom_id').action_check_availability()
        return orders
