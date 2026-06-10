# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP SFC BoM Comparison',
    'summary': 'Compare two Bills of Materials (EBoM to MBoM alignment)',
    'description': """
MRP SFC BoM Comparison
======================

Compares two bills of materials and reports the differences, to support the
Engineering BoM to Manufacturing BoM transition and reduce shop-floor
surprises.

Two modes:

* Single level: compares the direct component lines of each BoM.
* Multi-level summarized: explodes both BoMs (kits/phantoms expanded) and
  compares the total leaf-component requirements.

Each result line shows the quantity in each BoM, the delta, and whether the
component was added, removed, or had its quantity changed.
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
        'views/mrp_bom_comparison_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
