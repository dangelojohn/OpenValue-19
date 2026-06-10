# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue MRO - MRP Integration',
    'summary': 'Link maintenance equipment to work centers',
    'description': """
OpenValue MRO - MRP Integration
===============================

Bridges MRO Maintenance with Manufacturing: a maintenance equipment can be
linked to a work center, and the work center shows a live count of its open
maintenance requests with a quick action to review them.

Auto-installs when both MRO Maintenance and Manufacturing are present.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing/Maintenance',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['openvalue_mro_maintenance', 'mrp'],
    'data': [
        'views/mrp_workcenter_views.xml',
        'views/maintenance_equipment_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
}
