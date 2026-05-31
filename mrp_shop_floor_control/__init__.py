# -*- coding: utf-8 -*-

from . import models
from . import wizards


def post_init_hook(env):
    """Seed a Floating Times record for every manufacturing warehouse.

    Odoo 17+ passes a ready-to-use ``env`` to post-init hooks (the old
    ``(cr, registry)`` signature was removed).
    """
    env['mrp.floating.times'].create_floating_times()
