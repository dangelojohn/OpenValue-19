# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue Inventory Turnover Report',
    'summary': 'Inventory turnover ratio per product over a period',
    'description': """
OpenValue Inventory Turnover Report
===================================

Computes, over a chosen date range, each storable product's outbound quantity
(stock leaving internal locations), its average on-hand inventory, and the
resulting turnover ratio (outbound / average inventory). Higher turnover means
faster-moving stock.
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
        'wizards/stock_turnover_report_views.xml',
    ],
    'application': False,
    'installable': True,
}
