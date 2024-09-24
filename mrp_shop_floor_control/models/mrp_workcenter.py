# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from plotly.offline import plot
import plotly.graph_objects as px

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'


    hours_uom = fields.Many2one('uom.uom', 'Hours', compute="_get_uom_hours")
    start_without_stock = fields.Boolean('No Availability Check', default=False)
    doc_count = fields.Integer("Number of attached documents", compute='_compute_attached_docs_count')
    capacity_chart = fields.Text("Workcenter Capacity Chart", compute="_get_capacity_chart")
    resource_calendar_id = fields.Many2one(domain="[('company_id','=',company_id)]")

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            calendar_domain = [('company_id', '=', self.company_id.id)]
            calendar_ids = self.env['resource.calendar'].search(calendar_domain)
            if calendar_ids:
                if self.resource_calendar_id and self.resource_calendar_id.id not in calendar_ids.ids:
                    self.resource_calendar_id = False

    def _get_first_available_slot(self, start_datetime, duration):
        from_date = start_datetime
        to_date = start_datetime + timedelta(minutes=duration)
        return from_date, to_date

    @api.constrains('name', 'code')
    def check_unique(self):
        wc_name = self.env['mrp.workcenter'].search([('name', '=', self.name)])
        if len(wc_name) > 1:
            raise UserError(_("Workcenter Name already exists"))
        if self.code:
            wc_code = self.env['mrp.workcenter'].search([('code', '=', self.code)])
            if len(wc_code) > 1:
                raise UserError(_("Workcenter Code already exists"))

    def _get_uom_hours(self):
        uom = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)
        for record in self:
            if uom:
                record.hours_uom = uom.id

    def _compute_attached_docs_count(self):
        attachment = self.env['ir.attachment']
        for workcenter in self:
            workcenter.doc_count = attachment.search_count(['&',('res_model', '=', 'mrp.workcenter'), ('res_id', '=', workcenter.id)])

    def attachment_tree_view(self):
        self.ensure_one()
        domain = ['&', ('res_model', '=', 'mrp.workcenter'), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'type': 'ir.actions.act_window',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    def _get_workcenter_capacity_data(self):
        capacity_data = self.env["mrp.workcenter.capacity"].search([("workcenter_id", "=", self.id)])
        return capacity_data

    def _get_capacity_requirements_by_days(self):
        self.ensure_one()
        capacity_data = self.sudo()._get_workcenter_capacity_data()
        capacity_requirements_by_days = {}
        capacity_available_by_days = {}
        capacity_requirements_dates = [dt.date() for dt in capacity_data.mapped("date_planned")]
        capacity_available_dates = [dt.date() for dt in capacity_data.mapped("date_planned")]
        for date in capacity_requirements_dates:
            capacity_requirements_by_days[date] = 0.0
        for date in capacity_available_dates:
            capacity_available_by_days[date] = 0.0
        for record in capacity_data:
            date = record.date_planned.date()
            capacity_requirements_by_days[date] += record.wo_capacity_requirements
            capacity_available_by_days[date] = record.wc_daily_available_capacity_cal
        return capacity_requirements_by_days, capacity_available_by_days

    def _get_capacity_chart(self):
        for record in self:
            capacity_requirements_by_days, capacity_available_by_days = record._get_capacity_requirements_by_days()
            if capacity_requirements_by_days or capacity_available_by_days:
                date_list = [date for date in capacity_requirements_by_days.keys()]
                requirements_list = [date for date in capacity_requirements_by_days.values()]
                available_list = [date for date in capacity_available_by_days.values()]
                max1 = max(requirements_list)
                max2 = max(available_list)
                max_value = 1.5*max([max1, max2])
                N = len(date_list)
                fig = px.Figure()
                fig.add_trace(px.Bar(
                    name = 'Capacity Requirements',
                    x=date_list,
                    y=requirements_list,
                    text=requirements_list,
                    #textposition='auto',
                    width=[1000*3600*24] * N
                ))
                fig.add_shape(type='line',
                    x0=fields.date.today(),
                    y0=0,
                    x1=fields.date.today(),
                    y1=1,
                    line=dict(color='grey', width=2),
                    xref='x',
                    yref='paper',
                )
                fig.add_annotation(
                    x=fields.date.today(),
                    y=max_value,
                    xref="x",
                    yref="y",
                    text="Today",
                    showarrow=False,
                    font=dict(
                        family="Courier New, monospace",
                        size=10,
                        color="#000000"
                        ),
                    align="left",
                )
                fig.add_trace(px.Scatter(
                    name = 'Available Capacity',
                    x = date_list,
                    y = available_list,
                    marker_color='#000000',
                ))
                fig.update_layout(
                    width=1000,
                    height=400,
                    title='Work Center Capacity Report',
                    yaxis=dict(
                            title='Capacity (Hours)',
                            titlefont_size=16,
                            tickfont_size=14,
                    ),
                    legend=dict(
                            x=1.0,
                            y=1.0,
                            bgcolor='rgba(255, 255, 255, 0)',
                            bordercolor='rgba(255, 255, 255, 0)'
                    ),
                    xaxis_tickangle=-45,
                )
                record.capacity_chart = plot(figure_or_data=fig, include_plotlyjs=False, output_type='div')
            else:
                record.capacity_chart = _("No capacity load detected.")

