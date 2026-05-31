# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    milestone = fields.Boolean(
        'Milestone', default=False,
        help="A milestone operation closes all preceding operations of the "
             "manufacturing order when it is finished. No parallel operation "
             "(same sequence) is allowed on a milestone.")

    @api.constrains('milestone', 'sequence')
    def _check_milestone(self):
        for operation in self:
            siblings = self.search([
                ('bom_id', '=', operation.bom_id.id),
                ('id', '!=', operation.id),
                ('sequence', '=', operation.sequence),
            ])
            if operation.milestone and siblings:
                raise ValidationError(_(
                    "No parallel operation is allowed for a milestone "
                    "(operation '%s').", operation.display_name))
            if siblings.filtered('milestone'):
                raise ValidationError(_(
                    "No parallel operation is allowed for a milestone "
                    "(operation '%s' shares its sequence with a milestone).",
                    operation.display_name))
