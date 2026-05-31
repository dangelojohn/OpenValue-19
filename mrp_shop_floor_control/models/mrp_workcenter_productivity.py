# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpWorkcenterProductivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    setup_duration = fields.Float('Setup Duration')
    teardown_duration = fields.Float('Cleanup Duration')
    working_duration = fields.Float('Working Duration')
    overall_duration = fields.Float(
        'Overall Duration', compute='_compute_overall_duration', store=True)

    @api.depends('setup_duration', 'teardown_duration', 'working_duration')
    def _compute_overall_duration(self):
        for record in self:
            record.overall_duration = (
                record.setup_duration + record.teardown_duration + record.working_duration)
