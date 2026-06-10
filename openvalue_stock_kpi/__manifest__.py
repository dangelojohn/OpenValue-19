# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue Stock KPI',
    'summary': 'Inventory KPI dashboard',
    'description': """
OpenValue Stock KPI
===================

A quick inventory KPI dashboard: total on-hand value, number of products in
stock, and number of products with a negative forecast. Computed live when the
dashboard is opened.
""",
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/stock_kpi_views.xml',
    ],
    'application': False,
    'installable': True,
}
