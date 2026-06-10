# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue MRP Planning - Subcontracting',
    'summary': 'Subcontract replenishment proposals from planning shortages',
    'description': """
OpenValue MRP Planning - Subcontracting
=======================================

Extends the MRP Planning Engine for subcontracted products: when a planned
product is produced through a subcontracting bill of materials, the planning
line is routed as Subcontract instead of Manufacture, and releasing it raises a
purchase order to the subcontractor for the suggested quantity.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['openvalue_mrp_planning_engine', 'mrp_subcontracting'],
    'data': [],
    'application': False,
    'installable': True,
}
