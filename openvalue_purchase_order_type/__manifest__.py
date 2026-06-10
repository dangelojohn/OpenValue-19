# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue Purchase Order Type',
    'summary': 'Classify purchase orders by type',
    'description': """
OpenValue Purchase Order Type
=============================

Adds a configurable *type* to purchase orders (e.g. Standard, Subcontracting,
Investment, Service), so orders can be classified, filtered, grouped and
reported per type.
""",
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_type_views.xml',
        'views/purchase_order_views.xml',
    ],
    'application': False,
    'installable': True,
}
