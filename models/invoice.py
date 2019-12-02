# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    diancode_id = fields.Many2one('dian.document', string="Código DIAN", readonly=True)
    state_dian_document = fields.Selection(string="Estado documento DIAN", related='diancode_id.state')
    shipping_response = fields.Selection(string="Respuesta de envío DIAN", related='diancode_id.shipping_response')
    response_document_dian = fields.Selection(string="Respuesta de consulta DIAN", related='diancode_id.response_document_dian')
    email_response = fields.Selection(string='Decisión del cliente', related='diancode_id.email_response')
    response_message_dian = fields.Text(string='Mensaje de respuesta DIAN', related='diancode_id.response_message_dian')

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


    @api.multi
    def action_invoice_open(self):
        mensaje = ''
        rec = super(AccountInvoice, self).action_invoice_open()

        # Verifica datos de la resolucion DIAN
        if self.resolution_number == False:
            mensaje += '- La factura no tienen resolución DIAN asociada.' + '\n'
        rec_resolution_invoice = self.env['ir.sequence.dian_resolution'].search([('resolution_number', '=', self.resolution_number)])
        if not rec_resolution_invoice:
            mensaje += '- La resolución DIAN asociada a la factura no existe.' + '\n'
        if not rec_resolution_invoice.technical_key:
            mensaje += '- La resolución DIAN no tiene asociada la clave técnica.' + '\n'
        
        # Verifica datos de la compañia
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        company = self.env['res.company'].search([('id', '=', user.company_id.id)])
        partner = company.partner_id 
        if not company.document_repository:
            mensaje += '- Se debe asociar un repositorio en donde se almacenarán los archivos de FE.' + '\n'
        if not company.software_identification_code:
            mensaje += '- No se encuentra registrado el código de identificación del software.' + '\n'
        if not company.password_environment:
            mensaje += '- No se encuentra registrado el password del ambiente.' + '\n'
        if not partner.country_id.code:
            mensaje += '- Su empresa no tiene registrado el país.' + '\n'
        if not partner.xidentification:
            mensaje += '- Su empresa no tiene registrado el NIT.' + '\n'
        if not partner.company_type:
            mensaje += '- Su empresa no está identificada como persona juríduca o persona natural.' + '\n'
        if not partner.doctype:
            mensaje += '- Su empresa no tiene asociada un tipo de documento.' + '\n'
        if not partner.state_id:
            mensaje += '- Su empresa no tiene asociada un estado.' + '\n'
        if not partner.xcity:
            mensaje += '- Su empresa no tiene asociada un municipio.' + '\n'
        if not partner.street:
            mensaje += '- Su empresa no tiene asocida una dirección.' + '\n'
        if not company.trade_name:
            mensaje += '- Su empresa no tiene definida una razón social.' + '\n'
        # if not partner.x_pn_retri:
        #     mensaje += '- Su empresa no tiene definida un regimén tributario.' + '\n'
        if not company.digital_certificate:
            mensaje += '- No se ha registrado el certificado digital.' + '\n'
        if not company.certificate_key:
            mensaje += '- No se ha registrado la clave del certificado.' + '\n'
        if not company.issuer_name:
            mensaje += '- No se ha registrado el proveedor del certificado.' + '\n'
        if not company.serial_number:
            mensaje += '- No se ha registrado el serial del certificado.' + '\n'

        # Verifica datos del cliente
        if not self.currency_id.name:
            mensaje += '- El cliente no posee una moneda asociada.' + '\n'
        if not self.partner_id.company_type:
            mensaje += '- No se ha definido si el cliente es una persona natural o juridica.' + '\n'
        if not self.partner_id.xidentification:
            mensaje += '- El cliente no tiene registrado el NIT.' + '\n'
        if not self.partner_id.doctype:
            mensaje += '- El cliente no tiene asociada un tipo de documento.' + '\n'
        if not self.partner_id.country_id.code:
            mensaje += '- El cliente no tiene asociada un país.' + '\n'
        if not self.partner_id.state_id.name:
            mensaje += '- El cliente no tiene asociada un estado.' + '\n'
        if not self.partner_id.city:
            mensaje += '- El cliente no tiene asociada una ciudad.' + '\n'
        if not self.partner_id.xcity.name:
            mensaje += '- El cliente no tiene asociada un municipio.' + '\n'
        if not self.partner_id.street:
            mensaje += '- El cliente no tiene asociada una dirección.' + '\n'
        # if not self.partner_id.x_pn_retri:
        #     mensaje += '- El cliente no tiene definido un regimén tributario.' + '\n'
        if not self.partner_id.email:
            mensaje += '- El cliente no tiene definido un email.' + '\n'

        # Verifica que existan asociados impuestos al grupo de impuestos IVA, ICA y ICO       
        rec_account_invoice_tax = self.env['account.invoice.tax'].search([('invoice_id', '=', self.id)])
        if rec_account_invoice_tax:
            for item_tax in rec_account_invoice_tax:
                if item_tax.tax_id.tax_group_fe not in ('iva_fe','ica_fe','ico_fe'):
                    mensaje += '- La factura contiene impuestos que no están asociados al grupo de impuestos DIAN FE.' + '\n'

        if mensaje:
            raise ValidationError(mensaje)

        super(AccountInvoice, self).action_invoice_open()


    @api.multi
    def valitade_dian(self):
        # document_dian = self.env['dian.document'].search([('document_id', '=', self.id)])
        # if document_dian.state == ('por_notificar'):
        #     document_dian.send_pending_dian(document_dian.id,document_dian.document_type)
        # elif document_dian.state == 'por_validar':
        #     document_dian.request_validating_dian(document_dian.id)
        document_dian = self.env['dian.document'].search([('document_id', '=', self.id)])
        if document_dian.state == ('por_notificar'):
            document_dian.send_pending_dian(document_dian.id,document_dian.document_type)
        if document_dian.state == 'por_validar':
            document_dian.request_validating_dian(document_dian.id)


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    diancode_id = fields.Many2one('dian.document', string='Código DIAN')


    def _select(self):
        return  super(AccountInvoiceReport, self)._select() + ", sub.diancode_id as diancode_id"


    def _sub_select(self):
        return  super(AccountInvoiceReport, self)._sub_select() + ", ai.diancode_id as diancode_id"


    def _group_by(self):
        return super(AccountInvoiceReport, self)._group_by() + ", ai.diancode_id"
