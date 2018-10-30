# -*- coding: utf-8 -*-
from openerp import api, fields, models, _

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    diancode_id = fields.Many2one('dian.document', string="Código DIAN", readonly=True)


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


    @api.multi
    def invoice_dian_print(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'l10n_co_e-invoice.report_invoice_dian')


    @api.multi
    def action_invoice_dian_resend(self):
        """ Open a window to compose an email, with the edi invoice dian template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('l10n_co_e-invoice.email_template_edi_invoice_dian', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    diancode_id = fields.Many2one('dian.document', string='Código DIAN')


    def _select(self):
        return  super(AccountInvoiceReport, self)._select() + ", sub.diancode_id as diancode_id"


    def _sub_select(self):
        return  super(AccountInvoiceReport, self)._sub_select() + ", ai.diancode_id as diancode_id"


    def _group_by(self):
        return super(AccountInvoiceReport, self)._group_by() + ", ai.diancode_id"
