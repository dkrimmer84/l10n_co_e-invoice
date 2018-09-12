# -*- coding: utf-8 -*-
from openerp import api, fields, models, _

class Company(models.Model):
    _inherit = 'res.company'
    _name = 'res.company'

    trade_name = fields.Char(string="Razón social", required=True, default="")
    digital_certificate = fields.Char(string="Certificado digital", required=True, default="")
    software_identification_code = fields.Char(string="Código de identificación del software", required=True, default="")
    software_pin = fields.Char(string="PIN del software", required=True, default="")
    seed_code = fields.Char(string="Código de semilla", required=True, default="")
    