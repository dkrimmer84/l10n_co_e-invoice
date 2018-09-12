# -*- coding: utf-8 -*-
from openerp import api, fields, models, _

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    diancode_id = fields.Many2one('dian.document', string="Código DIAN", readonly=True)


    def print_e_invoice(self):
    	return True


    @api.multi
    def write(self, vals):
    	before_state = self.state
    	super(AccountInvoice, self).write(vals)
    	after_state = self.state

    	if before_state == 'draft' and after_state == 'open' and self.type == 'out_invoice':
    		new_dian_document = self.env['dian.document'].create({'document_id' : self.id, 'document_type' : 'f'})

    	if before_state == 'draft' and after_state == 'open' and self.type == 'out_refund':
    		new_dian_document = self.env['dian.document'].create({'document_id' : self.id, 'document_type' : 'c'})
    	return True
