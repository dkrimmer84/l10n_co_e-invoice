# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SequnceDateRange(models.Model):
    _inherit = 'ir.sequence.dian_resolution'
    _name = 'ir.sequence.dian_resolution'

    technical_key = fields.Char(string="Clave técnica", required = True)    