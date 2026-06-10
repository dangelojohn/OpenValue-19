# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue MRP Planning - Make to Order',
    'summary': 'Track released planned orders for delays and shortages',
    'description': """
OpenValue MRP Planning - Make to Order
======================================

Extends the MRP Planning Engine with make-to-order follow-up: each released
planned line tracks the scheduled date of its generated manufacturing or
purchase order and flags it as delayed when that date is later than the planned
(need) date. An MTO Monitor lists the released lines so a planner can spot
shortages and delays.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['openvalue_mrp_planning_engine'],
    'data': ['views/mrp_planning_mto_views.xml'],
    'application': False,
    'installable': True,
}
