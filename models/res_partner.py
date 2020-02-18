# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date

class ResPartner(models.Model):
    _inherit = 'res.partner'
    _name = 'res.partner'

    tribute_id = fields.Many2one('dian.tributes', string="Tributos", required = True)
    fiscal_responsability_ids = fields.Many2many('dian.fiscal.responsability', string="Responsabilidad fiscal", required = True)
    is_foreign = fields.Char('Is foreign')

    