# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date



class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    type = fields.Selection([('url', 'URL'), ('binary', 'File'),('out_invoice', 'Out Invoice'),('out_refund', 'Out Refund')],
        string='Type', required=True, default='binary', change_default=True)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    operation_type = fields.Selection([('01','Combustible'),('02','Emisor es Autoretenedor'),('03','Excluidos y Exentos'),
    ('04','Exportación'),('05','Generica'),('06','Generica con pago anticipado'),
    ('07','Generica con periodo de facturacion'),('08','Consorcio'),('09','Servicios AIU'),('10','Estandar'),
    ('11','Mandatos bienes'),('12','Mandatos Servicios'),('00', 'No Aplica')], string='Tipo de operación DIAN')
	
    product_UNSPSC_id = fields.Many2one('dian.unspsc.product', string="Producto UNSPSC")
    segment_name = fields.Char(string="Segmento UNSPSC", readonly=True, related='product_UNSPSC_id.segment_id.name')
    family_name = fields.Char(string="Familia UNSPSC", readonly=True, related='product_UNSPSC_id.family_id.name')
    class_name = fields.Char(string="Segmento UNSPSC", readonly=True, related='product_UNSPSC_id.class_id.name')