# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class DianFiscalResponsability(models.Model):
    _name = 'dian.fiscal.responsability'
    _description = 'Model DIAN Fiscal Responsability'

    code = fields.Char(string="Código Responsabilidad Fiscal DIAN", required=True)
    name = fields.Char(string="Significado Responsabilidad Fiscal DIAN", required=True)