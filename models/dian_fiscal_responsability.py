# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class DianFiscalResponsability(models.Model):
	_name = 'dian.fiscal.responsability'
	_description = 'Model DIAN Fiscal Responsability'
	_rec_name = 'code_name'

	code = fields.Char(string="Código Responsabilidad Fiscal DIAN", required=True)
	name = fields.Char(string="Significado Responsabilidad Fiscal DIAN", required=True)
	code_name = fields.Char(string="Código y nombre Resposabilidad Fiscal", compute = "_code_name", store = True) 


	@api.depends('code','name')
	def _code_name(self):		
		for rec_fiscal_responsability in self:
			rec_fiscal_responsability.code_name = rec_fiscal_responsability.code + '-' + rec_fiscal_responsability.name
		return 