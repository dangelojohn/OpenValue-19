# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
  'name': 'MRP Product Costing',
  'summary': 'MRP Product Costing',
  'version': '19.0.1.0.0',
  'category': 'Manufacturing',
  'website': 'www.openvalue.cloud',
  'author': "OpenValue",
  'support': 'info@openvalue.cloud',
  'license': "Other proprietary",
  'price': 1500.00,
  'currency': 'EUR',
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
  'application': False,
  'installable': True,
  'auto_install': False,
  'images': ['static/description/banner.png'],
}
