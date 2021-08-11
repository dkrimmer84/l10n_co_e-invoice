# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date

class ProductBrand(models.Model):
    _name = "product.brand"

    name = fields.Char('Marca', required = True)

class ProductModel(models.Model):
    _name = "product.model"


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    type = fields.Selection([('url', 'URL'), ('binary', 'File'),('out_invoice', 'Out Invoice'),('out_refund', 'Out Refund')],
        string='Type', required=True, default='binary', change_default=True)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    operation_type = fields.Selection([('09','Servicios AIU'),('10','Estandar'),
    ('11','Mandatos bienes')], string='Tipo de operación DIAN')
	
    product_UNSPSC_id = fields.Many2one('dian.unspsc.product', string="Producto UNSPSC")
    segment_name = fields.Char(string="Segmento UNSPSC", readonly=True, related='product_UNSPSC_id.segment_id.name')
    family_name = fields.Char(string="Familia UNSPSC", readonly=True, related='product_UNSPSC_id.family_id.name')
    class_name = fields.Char(string="Segmento UNSPSC", readonly=True, related='product_UNSPSC_id.class_id.name')

    brand_id = fields.Many2one('product.brand', 'Marca')
    model_id = fields.Many2one('product.model', 'Modelo')