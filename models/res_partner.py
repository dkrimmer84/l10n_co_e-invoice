# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date

class ResPartner(models.Model):
    _inherit = 'res.partner'
    _name = 'res.partner'

    tributes = fields.Selection([('01','IVA'), ('02','IC'), ('03','ICA'), ('04','INC'), ('05','ReteIVA'), ('06','ReteFuente'),
                            ('07','ReteICA'), ('08','ReteCREE'), ('20','FtoHorticultura'), ('21','Timbre'),
                            ('22','Bolsas'), ('23','INCarbono'), ('24','INCombustibles'),
                            ('25','Sobretasa Combustibles'), ('26','Sordicom'),
                            ('ZZ','Nombre de la figura tributaria')
                    ],string="Tributo DIAN", required = True)
    fiscal_responsability_id = fields.Many2one('dian.fiscal.responsability', string="Responsabilidad fiscal", required = True)
    #is_foreign = fields.Char('Is foreign')