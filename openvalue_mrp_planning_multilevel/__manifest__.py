# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue MRP Planning - Multi-level',
    'summary': 'Explode dependent demand through the BoM (multi-level MRP)',
    'description': """
OpenValue MRP Planning - Multi-level
====================================

Extends the MRP Planning Engine with multi-level (dependent demand) netting.
After the reorder-point run proposes planned manufacturing orders, this module
explodes each proposed order through its bill of materials, nets the resulting
component requirement against the component's availability, and proposes the
component supply in turn - recursively down the product structure. The result
is a complete multi-level plan from finished goods to purchased components.
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
