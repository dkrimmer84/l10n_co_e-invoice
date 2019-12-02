# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError

class AccountTax(models.Model):
    _inherit = 'account.tax'
    _name = 'account.tax'

    tax_group_fe = fields.Selection([('iva_fe','IVA FE'), ('ica_fe','ICA FE'), ('ico_fe','ICO FE'), ('nap_fe','No palica a DIAN FE')], 
        string="Grupo de impuesto DIAN FE", default='nap_fe')