# -*- coding: utf-8 -*-
# Copyright (c) Open Value - All Rights Reserved
# Rebuilt and refactored for Odoo 19.0 Community Edition.
{
    'name': 'MRP Product Costing',
    'summary': 'Standard / planned / actual manufacturing cost analysis, '
               'variance and overhead postings, and economical closure.',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'website': 'https://www.openvalue.cloud',
    'author': 'OpenValue',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': [
        'stock_account',
        'purchase_stock',
        'mrp_account',
        'analytic',
        'mrp_shop_floor_control',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_product_costing_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
