# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP SFC Substitution Costing',
    'summary': 'Quantify the cost impact of component substitutions',
    'description': """
MRP SFC Substitution Costing (bridge)
=====================================

Glue between MRP SFC BoM Component Substitution and MRP Product Costing.

When a component is substituted, MRP Product Costing already captures the cost
difference automatically: the actual material cost reads the swapped move's
product standard price, so the material variance reflects the substitute. This
bridge adds an explicit ``substitution_cost_delta`` on the order quantifying
how much of that variance is attributable to substitutions (substitute price
minus original component price, times quantity).

Auto-installs when both modules are present.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': [
        'mrp_sfc_bom_component_substitution',
        'mrp_product_costing',
    ],
    'data': [],
    'application': False,
    'installable': True,
    'auto_install': True,
}
