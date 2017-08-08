from openerp import api
from openerp.osv import osv, fields
from openerp.tools.translate import _


class product_production(osv.osv):
	_name = "product.production"
	_description = "Direct Production"
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	# def _total_sheets(self, cr, uid, ids, field_name, arg, context=None):
	#     result = dict.fromkeys(ids, 0)
	#     for bon in self.browse(cr, uid, ids):
	#         result[bon.id] = bon.end_at - bon.start_from + 1
	#     return result
	def _get_main_finished_product(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		# for rec in self.browse(cr, uid, ids, context=context):
		# 	result[rec.id] = (rec.company_id.currency_id.id, rec.company_id.currency_id.symbol)
		return result
	
	@api.model
	def _domain_production_location_id(self):
		data_obj = self.env['ir.model.data']
		stock_location_obj = self.env['stock.location']
		result = []
		
		virtual_location = data_obj.get_object_reference('stock', 'stock_location_locations_virtual')[1]
		virtual_location_child_ids = stock_location_obj.search([('id', 'child_of', virtual_location)]).ids
		result.append(('id', 'in', virtual_location_child_ids))
		return result
	
	_columns = {
		'create_date': fields.datetime('Production Date'),
		'employee_id': fields.many2one('hr.employee', 'Employee', required=True, ondelete='restrict'),
		'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete='restrict'),
		'production_location_id': fields.many2one('stock.location', 'Production Location', required=True,
			ondelete='restrict',
			domain=_domain_production_location_id),
		'raw_product_line_ids': fields.one2many('product.production.raw', 'production_id', 'Raw Products'),
		'finished_product_line_ids': fields.one2many('product.production.finished', 'production_id', 'Finished Products'),
		'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('finished', 'Finished')], 'State',
			required=True, ondelete='restrict'),
		'main_finished_product': fields.function(_get_main_finished_product, type='many2one', relation='product.product',
			store=True, string='Main Finished Product', required=True, ondelete='restrict'),
		'notes': fields.text('Notes'),
	}
	
	_defaults = {
		'production_location_id': lambda self, cr, uid, *args: self.pool.get('ir.model.data').get_object_reference(cr, uid,
			'product_production', 'stock_location_virtual_direct_production')[1],
		'state': 'draft',
	}
	
	# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def action_confirm(self, cr, uid, ids, context=None):
		# Harus dicek dulu di stock location ybs apakah bahan mentah tersedia sesuai qty dan uom yang diminta
		is_raw_product_available = True  # TODO
		if is_raw_product_available:
			self.write(cr, uid, ids, {'state': 'confirmed'})
		else:
			raise osv.except_orm(_('Confirm Failed'), _('There is not enough raw product available'))
	
	def action_finish(self, cr, uid, ids, context=None):
		# TODO create satu stock picking sampai state nya menjadi Transferred untuk seluruh bahan mentah, move dari location_id ke production_location_id
		# TODO create satu stock picking sampai state nya menjadi Transferred untuk seluruh barang jadi, move dari production_location_id ke location_id
		self.write(cr, uid, ids, {'state': 'finished'})


# ==========================================================================================================================

class product_production_raw(osv.osv):
	_name = "product.production.raw"
	_description = "Product Production Raw"
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'production_id': fields.many2one('product.production', 'Production'),
		'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='restrict'),
		'qty': fields.float('Qty.'),
		'uom_id': fields.many2one('product.uom', 'UoM', required=True, ondelete='restrict'),
	}
	
	# ONCHANGES ----------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		res = {'value': {}}
		if not product_id:
			return res
		product = self.pool.get('product.product').browse(cr, uid, [product_id], context=context)
		res['value'].update({'uom_id': product.uom_id.id})
		return res


# ==========================================================================================================================

class product_production_finished(osv.osv):
	_name = "product.production.finished"
	_description = "Product Production Finished"
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'production_id': fields.many2one('product.production', 'Production'),
		'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='restrict'),
		'qty': fields.float('Qty.'),
		'uom_id': fields.many2one('product.uom', 'UoM', required=True, ondelete='restrict'),
	}
	
	# ONCHANGES ----------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		res = {'value': {}}
		if not product_id:
			return res
		product = self.pool.get('product.product').browse(cr, uid, [product_id], context=context)
		res['value'].update({'uom_id': product.uom_id.id})
		return res
