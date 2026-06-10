# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP SFC BoM Component Substitution',
    'summary': 'Substitute equivalent components on stockout or discontinuation',
    'description': """
MRP SFC BoM Component Substitution
==================================

Keeps manufacturing orders runnable when a component is unavailable.

Each bill-of-material line can declare one or more substitute products, each
with an optional validity window. When an order's component is short, the
substitution action swaps the raw-material move to the first valid substitute
that is in stock, recording the original product for traceability.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': [
        'mrp_shop_floor_control',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_bom_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
