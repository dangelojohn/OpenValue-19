# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP Shop Floor Control',
    'summary': 'MRP Shop Floor Control',
    'version': '16.3.2.1',
    'category': 'Manufacturing',
    'website': 'www.openvalue.cloud',
    'author': "OpenValue",
    'support': 'info@openvalue.cloud',
    'license': "Other proprietary",
    'price': 2000.00,
    'currency': 'EUR',
    'depends': [
            'mrp',
    ],
    'demo': [],
    'data': [
        'security/mrp_workorder_confirmation_security.xml',
        'security/ir.model.access.csv',
        'views/stock_warehouse_views.xml',
        'views/mrp_floating_times_views.xml',
        # 'views/mrp_workcenter_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_routing_workcenter_views.xml',
        'views/mrp_workorder_views.xml',
        'views/mrp_workcenter_capacity_views.xml',
        'wizards/mrp_starting_views.xml',
        'wizards/mrp_confirmation_views.xml',
        'wizards/mrp_capacity_check_views.xml',
        'views/mrp_production_views.xml',
    ],
    "external_dependencies": {
        "python": ["plotly>=5.1.0"],
    },
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_backend': [
            'mrp_shop_floor_control/static/src/js/widget_plotly.js',
            'mrp_shop_floor_control/static/lib/plotly/plotly-latest.min.js',
        ],
    },
    'application': False,
    'installable': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
