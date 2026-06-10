# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue MRP Planning Engine',
    'summary': 'Transparent net-requirements planning with reviewable orders',
    'description': """
OpenValue MRP Planning Engine
=============================

A transparent material-requirements planning run. For each product with a
reordering rule, it compares the forecast availability against the rule's
minimum and proposes a planned order (rounded to the order multiple) to bring
stock back to the maximum. Each proposed line shows the requirement and the
supply route (manufacture if the product has a bill of materials, otherwise
purchase) and can be released individually into a draft manufacturing or
purchase order.

This is the pull (reorder-point) core of the OpenValue Planning Engine; the
Capacity Load, Make-to-Order and Subcontracting modules build on it.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['mrp', 'purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_planning_run_views.xml',
    ],
    'application': False,
    'installable': True,
}
