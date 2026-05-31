# -*- coding: utf-8 -*-
# Copyright (c) Open Value - All Rights Reserved
# Rebuilt and refactored for Odoo 19.0 Community Edition.
{
    'name': 'MRP Shop Floor Control',
    'summary': 'Forward/backward MO scheduling, work-order sequencing with '
               'milestones, work-center capacity load and shop-floor confirmation.',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'website': 'https://www.openvalue.cloud',
    'author': 'OpenValue',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': [
        'mrp',
    ],
    'data': [
        'security/mrp_shop_floor_control_security.xml',
        'security/ir.model.access.csv',
        'views/stock_warehouse_views.xml',
        'views/mrp_floating_times_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_routing_workcenter_views.xml',
        'views/mrp_workorder_views.xml',
        'views/mrp_workcenter_load_views.xml',
        'wizards/mrp_starting_views.xml',
        'wizards/mrp_confirmation_views.xml',
        'wizards/mrp_capacity_check_views.xml',
        'views/mrp_production_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mrp_shop_floor_control/static/lib/plotly/plotly.min.js',
            'mrp_shop_floor_control/static/src/js/plotly_chart_field.js',
            'mrp_shop_floor_control/static/src/xml/plotly_chart_field.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
