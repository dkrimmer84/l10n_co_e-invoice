# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class DianUNSPSCSegment(models.Model):
	_name = 'dian.unspsc.segment'
	_description = 'Model DIAN Segmento UNSPSC'

	segment = fields.Char(string="Código de segmento UNSPSC DIAN", required=True)
	name = fields.Char(string="Nombre de segmento UNSPSC DIAN", required=True)
	#product_UNSPSC_id = Many2one('dian.unspsc.product', 'segment_unspsc_id', string="product UNSPSC")


class DianUNSPSCFamily(models.Model):
	_name = 'dian.unspsc.family'
	_description = 'Model DIAN Familia UNSPSC'

	family = fields.Char(string="Código de familia UNSPSC DIAN", required=True)
	name = fields.Char(string="Nombre de familia UNSPSC DIAN", required=True)


class DianUNSPSCClass(models.Model):
	_name = 'dian.unspsc.class'
	_description = 'Model DIAN clase UNSPSC'

	classe = fields.Char(string="Código de clase UNSPSC DIAN", required=True)
	name = fields.Char(string="Nombre de clase UNSPSC DIAN", required=True)


class DianUNSPSCProduct(models.Model):
	_name = 'dian.unspsc.product'
	_description = 'Model DIAN producto UNSPSC'

	product = fields.Char(string="Código de producto UNSPSC DIAN", required=True)
	name = fields.Char(string="Nombre de producto UNSPSC DIAN", required=True)
	segment_id = fields.Many2one('dian.unspsc.segment', string="Segmento UNSPSC", required=True)
	family_id = fields.Many2one('dian.unspsc.family', string="Familia UNSPSC", required=True)
	class_id =  fields.Many2one('dian.unspsc.class', string="Clase UNSPSC", required=True)