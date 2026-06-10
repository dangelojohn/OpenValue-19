# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue Interwarehouse Transfer',
    'summary': 'Centralized stock transfer between warehouses',
    'description': """
OpenValue Interwarehouse Transfer
=================================

A single wizard to move a product quantity from one warehouse to another. It
creates an internal transfer (stock.picking) between the source and destination
warehouse stock locations, with centralized document control.
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
        'wizards/interwarehouse_transfer_views.xml',
    ],
    'application': False,
    'installable': True,
}
