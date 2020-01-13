# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    diancode_id = fields.Many2one('dian.document', string="Código DIAN", readonly=True)
    state_dian_document = fields.Selection(string="Estado documento DIAN", related='diancode_id.state')
    shipping_response = fields.Selection(string="Respuesta de envío DIAN", related='diancode_id.shipping_response')
    response_document_dian = fields.Selection(string="Respuesta de consulta DIAN", related='diancode_id.response_document_dian')
    email_response = fields.Selection(string='Decisión del cliente', related='diancode_id.email_response')
    response_message_dian = fields.Text(string='Mensaje de respuesta DIAN', related='diancode_id.response_message_dian')
    is_debit_note = fields.Boolean(string='Nota de débito', default=False)

    QR_code = fields.Binary(string='Código QR', readonly=True, related = 'diancode_id.QR_code')
    cufe = fields.Char(string='CUFE', readonly=True, related = 'diancode_id.cufe')

    @api.multi
    def write(self, vals):
        before_state = self.state
        super(AccountInvoice, self).write(vals)
        after_state = self.state

        if before_state == 'draft' and after_state == 'open' and self.type == 'out_invoice' and self.is_debit_note == False:
            new_dian_document = self.env['dian.document'].create({'document_id' : self.id, 'document_type' : 'f'})

        if before_state == 'draft' and after_state == 'open' and self.type == 'out_refund':
            new_dian_document = self.env['dian.document'].create({'document_id' : self.id, 'document_type' : 'c'})

        if before_state == 'draft' and after_state == 'open' and self.type == 'out_invoice' and self.is_debit_note == True:
            new_dian_document = self.env['dian.document'].create({'document_id' : self.id, 'document_type' : 'd'})
        
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
    def create_nota_debit(self):
        invoice_tax_lines_new = []
        invoice_new = self.env['account.invoice']
        invoice_new = invoice_new.create(
            {
            'journal' : self.journal_id.id,
            'partner_id' : self.partner_id.id,
            'company_id' : self.company_id.id,
            'state' : 'draft',
            'type' : self.type,
            'sent' : self.sent,
            'origin' : self.number,
            'account_id' : self.account_id.id,
            'date_invoice' : date.today(),
            'payment_term_id' : self.payment_term_id.id,
            'date' : date.today(),
            'user_id' : self.env.uid,
            'currency_id' : self.currency_id.id,
            'commercial_partner_id' : self.commercial_partner_id.id,
            'partner_shipping_id' : self.partner_shipping_id.id,
            'team_id' : self.team_id.id,
            'resolution_date' : self.resolution_date,
            'resolution_date_to' : self.resolution_date_to,
            'resolution_number_from' : self.resolution_number_from,
            'resolution_number_to' : self.resolution_number_to,
            'resolution_number' : self.resolution_number,
            'is_debit_note' : True,
            })

        if invoice_new:
            for line_invoice in self.invoice_line_ids:
                invoice_line_new = []  
                invoice_tax_line_new = []
                for invoice_line_tax in line_invoice.invoice_line_tax_ids:
                    invoice_tax_line_new.append((0,0,{
                        'tax_id' : invoice_line_tax.id,
                     }))

                invoice_line_new.append((0,0,{
                    'move_id' : invoice_new.id, 
                    'origin' : line_invoice.origin, 
                    'price_unit' : line_invoice.price_unit, 
                    'price_subtotal' : line_invoice.price_subtotal, 
                    'currency_id' : line_invoice.currency_id.id,
                    'uom_id' : line_invoice.uom_id.id, 
                    'partner_id' : line_invoice.partner_id.id, 
                    'sequence' : line_invoice.sequence,  
                    'company_id' : line_invoice.company_id.id,  
                    'account_analytic_id' : line_invoice.account_analytic_id.id,  
                    'account_id' : line_invoice.account_id.id,  
                    'price_subtotal_signed' : line_invoice.price_subtotal_signed, 
                    'name' : line_invoice.name,  
                    'product_id' : line_invoice.product_id.id,  
                    'invoice_id' : line_invoice.invoice_id.id,
                    'quantity' : line_invoice.quantity,
                    #'layout_category_sequence' : line_invoice.layout_category_sequence,
                    #'layout_category_id' : line_invoice.layout_category_id.id,
                    'purchase_line_id' : line_invoice.purchase_line_id.id,
                    'invoice_line_tax_ids' : invoice_line_tax,
                    }))           
                invoice_new.invoice_line_ids = invoice_line_new               

            for invoice_tax_line in self.tax_line_ids:
                invoice_tax_lines_new.append((0,0,{
                    'account_id' : invoice_tax_line.account_id.id,
                    'name' : invoice_tax_line.name,
                    'sequence' : invoice_tax_line.sequence,
                    'invoice_id' : invoice_new.id,
                    'manual' : invoice_tax_line.manual,
                    'company_id' : invoice_tax_line.company_id.id,
                    'currency_id' : invoice_tax_line.currency_id.id,
                    'account_analytic_id' : invoice_tax_line.account_analytic_id.id,
                    'tax_id' : invoice_tax_line.tax_id.id,
                    'amount' : invoice_tax_line.amount,
                    }))
            invoice_new.tax_line_ids = invoice_tax_lines_new

        my_view = self.env.ref('account.invoice_form')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice',
            #'name' : self.name,
            'view_id': my_view.id,
            'view_mode': 'form',
            'res_id': invoice_new.id,
        }  


    @api.multi
    def action_invoice_open(self):
        mensaje = ''
        rec = super(AccountInvoice, self).action_invoice_open()
        if self.type == 'out_invoice':
            if self.is_debit_note:
                rec_sequence_nd = self.env['ir.sequence']
                self.number = rec_sequence_nd.next_by_code('nota_debito.sequence')
                self.move_name = self.number  
            # Verifica datos de la resolucion DIAN
            if self.resolution_number == False:
                mensaje += '- La factura no tienen resolución DIAN asociada.' + '\n'
            rec_resolution_invoice = self.env['ir.sequence.dian_resolution'].search([('resolution_number', '=', self.resolution_number)])
            if not rec_resolution_invoice:
                mensaje += '- La resolución DIAN asociada a la factura no existe.' + '\n'
            if not rec_resolution_invoice.technical_key:
                mensaje += '- La resolución DIAN no tiene asociada la clave técnica.' + '\n'
            # Verifica datos de la compañia
            company = self.company_id
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
            if not partner.tributes:
                mensaje += '- Su empresa no tiene asociada un tributo.' + '\n' 
            if not partner.fiscal_responsability_ids:
                mensaje += '- Su empresa no tiene asociada una responsabilidad fiscal.' + '\n' 
            if not company.operation_type:
                mensaje += '- Su empresa no tiene asociada un tipo de operación.' + '\n' 
            if not partner.xcity:
                mensaje += '- Su empresa no tiene asociada un municipio.' + '\n'
            if not partner.street:
                mensaje += '- Su empresa no tiene asocida una dirección.' + '\n'
            if not company.trade_name:
                mensaje += '- Su empresa no tiene definida una razón social.' + '\n'
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
            if not self.partner_id.fiscal_responsability_ids:
                mensaje += '- El cliente no tiene asociada una responsabilidad fiscal.' + '\n'
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
            if not partner.tributes:
                mensaje += '- El cliente no tiene asociada un tributo de los indicados en la tabla 6.2.2 Tributos indicado en la tabla 6.2.2 Tributos.' + '\n' 
            if not self.partner_id.email:
                mensaje += '- El cliente no tiene definido un email.' + '\n'
            # Verifica que existan asociados impuestos al grupo de impuestos IVA, ICA y ICO       
            rec_account_invoice_tax = self.env['account.invoice.tax'].search([('invoice_id', '=', self.id)])
            if rec_account_invoice_tax:
                for item_tax in rec_account_invoice_tax:
                    if item_tax.tax_id.tax_group_fe not in ('iva_fe','ica_fe','ico_fe','ret_fe'):
                        mensaje += '- La factura contiene impuestos que no están asociados al grupo de impuestos DIAN FE.' + '\n'
            data_lines_doc = self.env['account.invoice.line'].search([('invoice_id', '=', self.id)])
            if data_lines_doc:
                for data_line in data_lines_doc:
                    for line_tax in data_line.invoice_line_tax_ids:        
                        rec_tax = self.env['account.tax'].search([('id', '=', line_tax.id)])
                        if not rec_tax.tributes:
                            mensaje += '- Algunos impueso indicados en la factura no tiene un tributo asociado según los tributos indicados en la tabla 6.2.2 Tributos.' + '\n'
            if data_lines_doc:
                for data_line in data_lines_doc:
                    count_line_taxt = 0
                    for line_tax in data_line.invoice_line_tax_ids:        
                        count_line_taxt += 1
                    if count_line_taxt > 1:
                        mensaje += '- Existen líneas de factura que poseen más de un impuesto asociado' + '\n'
            if not self.payment_term_id:
                mensaje += '- La factura no tiene un término de pago definido' + '\n'
            if mensaje:
                raise ValidationError(mensaje)


    @api.multi
    def valitade_dian(self):
        document_dian = self.env['dian.document'].search([('document_id', '=', self.id)])
        if document_dian.state == ('por_notificar'):
            document_dian.send_pending_dian(document_dian.id,document_dian.document_type)
        if document_dian.state == 'rechazado':
            document_dian.response_message_dian = ' '
            document_dian.xml_response_dian = ' '
            document_dian.xml_send_query_dian = ' '
            document_dian.response_message_dian = ' '
            document_dian.xml_document = ' '
            document_dian.xml_file_name = ' '
            document_dian.zip_file_name = ' '
            document_dian.cufe = ' '
            document_dian.date_document_dian = ' '
            document_dian.write({'state' : 'por_notificar', 'resend' : False})
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
