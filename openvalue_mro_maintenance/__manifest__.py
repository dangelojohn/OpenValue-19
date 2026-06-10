# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'OpenValue MRO Maintenance',
    'summary': 'Maintenance strategies and scheduled maintenance plans',
    'description': """
OpenValue MRO Maintenance
=========================

Extends Odoo Maintenance for Maintenance, Repair & Operations:

* Additional maintenance strategies on requests: On Condition, Periodic,
  Retrofit (on top of the native Corrective / Preventive).
* Maintenance Plans: per-equipment scheduled plans with a strategy, an interval
  (days / weeks / months) and a next date. Generating a plan creates a
  maintenance request and rolls the next date forward.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing/Maintenance',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': ['maintenance'],
    'data': [
        'security/ir.model.access.csv',
        'views/maintenance_plan_views.xml',
    ],
    'application': False,
    'installable': True,
}
