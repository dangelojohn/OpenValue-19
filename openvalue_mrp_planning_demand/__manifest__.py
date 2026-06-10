# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue MRP Planning - Sales Demand',
    'summary': 'Drive planning from open sales-order demand (push)',
    'description': """
OpenValue MRP Planning - Sales Demand
=====================================

Adds independent (push) demand to the MRP Planning Engine. On top of the
reorder-point run, it collects the open sales-order demand per product
(ordered minus delivered), nets it against on-hand plus incoming supply and the
quantity already planned, and proposes the supply to cover the shortfall. When
the multi-level module is installed, the new demand is exploded through the
BoM as well, so customer demand drives a full multi-level plan.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['openvalue_mrp_planning_engine', 'sale_stock'],
    'data': ['views/mrp_planning_run_views.xml'],
    'application': False,
    'installable': True,
}
