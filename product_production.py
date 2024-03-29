from openerp import api
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta


class product_production(osv.osv):
	_name = "product.production"
	_description = "Direct Production"
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	def _get_main_finished_product(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for production in self.browse(cr, uid, ids, context):
			if len(production.finished_product_line_ids) > 0:
				result[production.id] = production.finished_product_line_ids[0].product_id.id
			else:
				result[production.id] = 0
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
	
	def _default_location_id(self, cr, uid, context={}):
		# default location adalah gudang tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.default_incoming_location_id.id or None
	
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
			store=True, string='Main Finished Product', ondelete='restrict'),
		'notes': fields.text('Notes'),
	}
	
	_defaults = {
		'create_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'production_location_id': lambda self, cr, uid, *args: self.pool.get('ir.model.data').get_object_reference(cr, uid,
			'product_production', 'stock_location_virtual_direct_production')[1],
		'state': 'draft',
		'location_id': _default_location_id,
	}
	
	# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def _get_product_qty(self, cr, uid, location_id=False, product_id=False, uom_id=False, context=None):
		if product_id and location_id:
			quant_obj = self.pool.get("stock.quant")
			uom_obj = self.pool.get("product.uom")
			product_obj = self.pool.get('product.product')
			users_obj = self.pool.get('res.users')
			
			product = product_obj.browse(cr, uid, product_id, context=context)
			company_id = users_obj.browse(cr, uid, uid, context=context).company_id.id
			dom = [('company_id', '=', company_id), ('location_id', '=', location_id), ('product_id','=', product_id)]
			quants = quant_obj.search(cr, uid, dom, context=context)
			th_qty = sum([x.qty for x in quant_obj.browse(cr, uid, quants, context=context)])
			if product_id and uom_id and product.uom_id.id != uom_id:
				th_qty = uom_obj._compute_qty(cr, uid, product.uom_id.id, th_qty, uom_id)
			return th_qty
	
	def action_confirm(self, cr, uid, ids, context=None):
		# cek di stock location ybs apakah bahan mentah tersedia sesuai qty dan uom yang diminta
		is_raw_product_available = True
		for production in self.browse(cr, uid, ids):
			for line in production.raw_product_line_ids:
				th_qty = self._get_product_qty(cr, uid, production.location_id.id, line.product_id.id, line.uom_id.id)
				if line.qty > th_qty:
					is_raw_product_available = False
					break
		if is_raw_product_available:
			return self.write(cr, uid, ids, {'state': 'confirmed'})
		else:
			raise osv.except_orm(_('Confirm Failed'), _('There is not enough raw product available'))
	
	def action_finish(self, cr, uid, ids, context=None):
		picking_obj = self.pool.get('stock.picking')
		model_obj = self.pool.get('ir.model.data')
		internal_picking = model_obj.get_object_reference(cr, uid, 'stock', 'picking_type_internal')[1]
		
		productions = self.browse(cr, uid, ids, context)
		for production in productions:
			# Create satu stock picking sampai state nya menjadi Transferred untuk seluruh bahan mentah,
			# move dari location_id ke production_location_id
			move_lines = []
			for raw_products in production.raw_product_line_ids:
				move_lines.append((0, False, {
					'product_id': raw_products.product_id.id,
					'product_uom_qty': raw_products.qty,
					'product_uom': raw_products.uom_id.id,
					'location_id': production.location_id.id,
					'location_dest_id': production.production_location_id.id,
					'name': raw_products.product_id.name
				}))
			vals = {
				'picking_type_id': internal_picking,
				'move_lines': move_lines,
			}
			picking_raw_id = picking_obj.create(cr, uid, vals, context)
			picking_raw = picking_obj.browse(cr, uid, [picking_raw_id], context)
			picking_raw.action_confirm()
			picking_raw.force_assign()
			picking_raw.do_transfer()
			# Create satu stock picking sampai state nya menjadi Transferred untuk seluruh barang jadi, move dari
			# production_location_id ke location_id
			move_lines = []
			for finished_products in production.finished_product_line_ids:
				move_lines.append((0, False, {
					'product_id': finished_products.product_id.id,
					'product_uom_qty': finished_products.qty,
					'product_uom': finished_products.uom_id.id,
					'location_id': production.production_location_id.id,
					'location_dest_id': production.location_id.id,	
					'name': finished_products.product_id.name
				}))
			vals = {
				'picking_type_id': internal_picking,
				'move_lines': move_lines,
			}
			picking_finished_id = picking_obj.create(cr, uid, vals, context)
			picking_finished = picking_obj.browse(cr, uid, [picking_finished_id], context)
			picking_finished.action_confirm()
			picking_finished.force_assign()
			picking_finished.do_transfer()
		return self.write(cr, uid, ids, {'state': 'finished'})


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
	
	_defaults = {
		'qty' : 1
	}
	
	# ONCHANGES ----------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		res = {'value': {}, 'domain': {}}
		if not product_id:
			return res
		product = self.pool.get('product.product').browse(cr, uid, [product_id], context=context)
		res['value'].update({'uom_id': product.uom_id.id})
		res['domain'].update({'uom_id': [('category_id', '=', product.uom_id.category_id.id)]})
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
	
	_defaults = {
		'qty' : 1
	}
	
	# ONCHANGES ----------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		res = {'value': {}, 'domain': {}}
		if not product_id:
			return res
		product = self.pool.get('product.product').browse(cr, uid, [product_id], context=context)
		res['value'].update({'uom_id': product.uom_id.id})
		res['domain'].update({'uom_id': [('category_id', '=', product.uom_id.category_id.id)]})
		return res
