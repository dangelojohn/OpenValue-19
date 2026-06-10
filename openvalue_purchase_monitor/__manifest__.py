# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue Purchase Monitor',
    'summary': 'Follow-up monitor for open purchase order lines',
    'description': """
OpenValue Purchase Monitor
==========================

A follow-up view over confirmed purchase order lines for the purchasing
follow-up process: outstanding quantity to receive, planned receipt date, and
a late flag (planned date passed while quantity is still pending). List + pivot
with filters and grouping by vendor.
""",
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['purchase'],
    'data': [
        'views/purchase_monitor_views.xml',
    ],
    'application': False,
    'installable': True,
}
