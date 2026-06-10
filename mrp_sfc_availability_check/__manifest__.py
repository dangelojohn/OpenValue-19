# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP SFC Availability Check',
    'summary': 'Material and capacity availability check + Master Production Plan',
    'description': """
MRP SFC Availability Check
==========================

Feasibility gating in front of Shop Floor Control execution.

Before a manufacturing order is released to the floor, this module verifies
that it can actually be made:

* Material availability: the bill of materials is exploded across all levels
  (kit/phantom BoMs included) and every leaf component's required quantity is
  compared with the free-to-use stock in the order's warehouse.
* Capacity availability: the routing operations are summed per work center and
  the required hours are compared with the remaining finite capacity in the
  order window (working calendar minus already-planned load).

A per-line shortage report is produced on the order, and a Master Production
Plan wizard batch-checks every draft/confirmed order in a date range so a
planner can see, at a glance, which orders are feasible.
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
        'report/mrp_availability_report.xml',
        'views/mrp_production_views.xml',
        'wizards/mrp_mps_report_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
