# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class Company(models.Model):
    _inherit = 'res.company'
    _name = 'res.company'


    def _get_dian_sequence(self):
        list_dian_sequence = []
        rec_dian_sequence = self.env['ir.sequence'].search([('company_id', '=', self.env.user.partner_id.company_id.id), ('use_dian_control', '=', True),('active', '=', True)])
        for sequence in rec_dian_sequence:
            list_dian_sequence.append((str(sequence.id), sequence.name))
        return list_dian_sequence


    trade_name = fields.Char(string="Razón social", required=True, default="")
    digital_certificate = fields.Text(string="Certificado digital público", required=True, default="")
    software_identification_code = fields.Char(string="Código de identificación del software", required=True, default="")
    identificador_set_pruebas = fields.Char(string = 'Identificador del SET de pruebas', required = True ) 
    
    software_pin = fields.Char(string="PIN del software", required=True, default="")
    password_environment = fields.Char(string="Clave de ambiente", required=True, default="")
    seed_code = fields.Integer(string="Código de semilla", required=True, default=5000000)
    issuer_name = fields.Char(string="Ente emisor del certificado", required=True, default="")
    serial_number = fields.Char(string="Serial del certificado", required=True, default="")
    document_repository = fields.Char(string='Ruta de almacenamiento de archivos', required=True)
    in_use_dian_sequence = fields.Selection('_get_dian_sequence', 'Secuenciador DIAN a utilizar', required=True)
    certificate_key = fields.Char(string='Clave del certificado P12', required=True, default="")
    operation_type = fields.Selection([('01','Combustible'),('02','Emisor es Autoretenedor'),('03','Excluidos y Exentos'),
    ('04','Exportación'),('05','Generica'),('06','Generica con pago anticipado'),
    ('07','Generica con periodo de facturacion'),('08','Consorcio'),('09','Servicios AIU'),('10','Estandar'),
    ('11','Mandatos bienes'),('12','Mandatos Servicios')], string='Tipo de operación DIAN', required=True)
    pem = fields.Char(string="Nombre del archivo PEM del certificado", required=True, default="")
    certificate = fields.Char(string="Nombre del archivo del certificado", required=True, default="")