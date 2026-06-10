# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP SFC External Operation',
    'summary': 'Outsource routing operations to vendors via Purchasing',
    'description': """
MRP SFC External Operation
==========================

Manages outsourced production activities by bridging Shop Floor Control with
Purchasing.

A routing operation can be flagged as *external*: instead of being executed
in-house on a work center, it is sent to a vendor. When the manufacturing
order is processed, a purchase order for the outsourced service is generated
for the vendor (one PO per vendor, one line per external work order), linked
back to the order and the work order.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': [
        'mrp_shop_floor_control',
        'purchase',
    ],
    'data': [
        'views/mrp_routing_workcenter_views.xml',
        'views/mrp_production_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
