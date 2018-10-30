# -*- coding: utf-8 -*-
from openerp import api, fields, models, _

class Company(models.Model):
    _inherit = 'res.company'
    _name = 'res.company'

    trade_name = fields.Char(string="Razón social", required=True, default="")
    digital_certificate = fields.Text(string="Certificado digital público", required=True, default="")
    software_identification_code = fields.Char(string="Código de identificación del software", required=True, default="")
    software_pin = fields.Char(string="PIN del software", required=True, default="")
    seed_code = fields.Integer(string="Código de semilla", required=True, default=5000000)
    issuer_name = fields.Char(string="Ente emisor del certificado", required=True, default="")
    serial_number = fields.Char(string="Serial del certificado", required=True, default="")
    document_repository = fields.Char(string='Ruta en donde se almacenaran los archivos que utiliza y genera la Facturación Electrónica')