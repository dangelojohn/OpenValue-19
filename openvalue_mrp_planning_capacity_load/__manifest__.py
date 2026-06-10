# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue MRP Planning - Capacity Load',
    'summary': 'Work-center capacity load of planned manufacturing',
    'description': """
OpenValue MRP Planning - Capacity Load
======================================

Extends the MRP Planning Engine: each planned manufacturing line shows the
work-center hours it would require (sum of the BoM operation times for the
suggested quantity), so a planner can see the capacity load implied by a
planning run before releasing the orders.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['openvalue_mrp_planning_engine'],
    'data': ['views/mrp_planning_run_views.xml'],
    'application': False,
    'installable': True,
}
