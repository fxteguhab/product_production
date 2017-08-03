# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
	'name': "Product Direct Production",
	'summary': """
		Product Direct Production
	""",
	'description': """
		Product Direct Production
	""",
	'author': 'Christyan Juniady and Associates',
	'maintainer': 'Christyan Juniady and Associates',
	'website': 'http://www.chjs.biz',
	'category': 'Uncategorized',
	'version': '0.1',
	'depends': ['base', 'hr', 'stock', 'product'],
	'data': [
		'views/product_production_view.xml',
		'menu/product_production_menu.xml',
		'data/product_production_data.xml',
	],
	'demo': [
	],
	'installable': True,
	'auto_install': True,
}
