# -*- coding: utf-8 -*-

import json

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    hours_uom = fields.Many2one('uom.uom', 'Hours', compute='_compute_hours_uom')
    start_without_stock = fields.Boolean(
        'No Availability Check', default=False,
        help="Allow starting a work order on this work center even if the "
             "components are not fully available.")
    doc_count = fields.Integer(
        "Number of attached documents", compute='_compute_attached_docs_count')
    capacity_chart = fields.Text(
        "Work Center Capacity Chart", compute='_compute_capacity_chart')

    def _compute_hours_uom(self):
        uom = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)
        for record in self:
            record.hours_uom = uom.id if uom else False

    def _sfc_capacity(self, product=None):
        """Flat capacity scalar for SFC cost/scheduling math.

        Odoo 19 removed the scalar ``mrp.workcenter.capacity`` field; capacity
        is now per-product via ``capacity_ids`` / ``_get_capacity``. We resolve
        the product-specific capacity when a product is known, else default 1.0.
        """
        self.ensure_one()
        if product:
            return self._get_capacity(product, product.uom_id, default_capacity=1)[0] or 1.0
        return 1.0

    def _compute_attached_docs_count(self):
        Attachment = self.env['ir.attachment']
        for workcenter in self:
            workcenter.doc_count = Attachment.search_count([
                ('res_model', '=', 'mrp.workcenter'),
                ('res_id', '=', workcenter.id),
            ])

    @api.constrains('name', 'code', 'company_id')
    def _check_unique_name_code(self):
        for workcenter in self:
            domain = [
                ('id', '!=', workcenter.id),
                ('company_id', '=', workcenter.company_id.id),
                ('name', '=', workcenter.name),
            ]
            if self.search_count(domain):
                raise ValidationError(_("Work Center Name already exists."))
            if workcenter.code:
                domain = [
                    ('id', '!=', workcenter.id),
                    ('company_id', '=', workcenter.company_id.id),
                    ('code', '=', workcenter.code),
                ]
                if self.search_count(domain):
                    raise ValidationError(_("Work Center Code already exists."))

    def attachment_tree_view(self):
        self.ensure_one()
        return {
            'name': _('Attachments'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', 'mrp.workcenter'), ('res_id', '=', self.id)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def _get_capacity_load_by_day(self):
        """Return ``(requirements_by_day, available_by_day)`` dicts keyed by
        date for this work center, built from the Shop Floor Control load
        records (``mrp.workcenter.load``)."""
        self.ensure_one()
        loads = self.env['mrp.workcenter.load'].sudo().search(
            [('workcenter_id', '=', self.id)])
        requirements = {}
        available = {}
        for load in loads:
            day = load.date_planned.date()
            requirements[day] = requirements.get(day, 0.0) + load.wo_capacity_requirements
            available[day] = load.wc_daily_available_capacity
        return requirements, available

    def _compute_capacity_chart(self):
        for workcenter in self:
            requirements, available = workcenter._get_capacity_load_by_day()
            if not requirements and not available:
                workcenter.capacity_chart = False
                continue
            days = sorted(set(requirements) | set(available))
            x = [day.isoformat() for day in days]
            req = [requirements.get(day, 0.0) for day in days]
            avail = [available.get(day, 0.0) for day in days]
            figure = {
                'data': [
                    {
                        'type': 'bar',
                        'name': _('Capacity Requirements'),
                        'x': x,
                        'y': req,
                        'text': [round(v, 2) for v in req],
                    },
                    {
                        'type': 'scatter',
                        'name': _('Available Capacity'),
                        'x': x,
                        'y': avail,
                        'marker': {'color': '#000000'},
                    },
                ],
                'layout': {
                    'height': 400,
                    'title': {'text': _('Work Center Capacity Report')},
                    'yaxis': {'title': {'text': _('Capacity (Hours)')}},
                    'xaxis': {'tickangle': -45},
                    'legend': {'x': 1.0, 'y': 1.0},
                    'barmode': 'group',
                },
            }
            workcenter.capacity_chart = json.dumps(figure)
