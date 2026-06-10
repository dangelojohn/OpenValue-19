# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue Stock Product Overview',
    'summary': 'Consolidated stock overview per product',
    'description': """
OpenValue Stock Product Overview
================================

A single consolidated view of each storable product's stock position:
on-hand, forecast, incoming, outgoing, free-to-use quantity, and on-hand value
(on-hand x cost). Available from Inventory > Reporting.
""",
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['stock'],
    'data': [
        'views/product_overview_views.xml',
    ],
    'application': False,
    'installable': True,
}
