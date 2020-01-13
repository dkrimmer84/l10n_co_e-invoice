# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountTax(models.Model):
    _inherit = 'account.tax'
    _name = 'account.tax'

    tax_group_fe = fields.Selection([('iva_fe','IVA FE'), ('ica_fe','ICA FE'), ('ico_fe','INC FE'), ('ret_fe','RET FE'), ('nap_fe','No palica a DIAN FE')], 
        string="Grupo de impuesto DIAN FE", default='nap_fe')
    tributes = fields.Selection([('01','IVA'), ('02','IC'), ('03','ICA'), ('04','INC'), ('05','ReteIVA'), ('06','ReteFuente'),
                            ('07','ReteICA'), ('08','ReteCREE'), ('20','FtoHorticultura'), ('21','Timbre'),
                            ('22','Bolsas'), ('23','INCarbono'), ('24','INCombustibles'),
                            ('25','Sobretasa Combustibles'), ('26','Sordicom'),
                            ('ZZ','Nombre de la figura tributaria')
                    ],string="Tributo DIAN")