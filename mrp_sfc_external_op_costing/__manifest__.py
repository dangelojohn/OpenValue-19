# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP SFC External Operation Costing',
    'summary': 'Feed outsourced-operation cost into the MO industrial cost',
    'description': """
MRP SFC External Operation Costing (bridge)
===========================================

Glue between MRP SFC External Operation and MRP Product Costing.

The cost of an outsourced operation is the purchase order amount, not in-house
labour. This bridge sums the confirmed external purchase-order lines of a
manufacturing order into ``external_direct_cost`` and adds it to the order's
full industrial cost at financial closure.

Auto-installs when both modules are present.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': [
        'mrp_sfc_external_operation',
        'mrp_product_costing',
    ],
    'data': [],
    'application': False,
    'installable': True,
    'auto_install': True,
}
