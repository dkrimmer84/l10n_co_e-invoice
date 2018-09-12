# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
from pytz import timezone
import logging

_logger = logging.getLogger(__name__)

try:
    from lxml import etree
except:
    print("Cannot import  etree")

from lxml.etree import Element, SubElement
from openerp.tools.translate import _

try:
    import shutil
except:
    print("Cannot import shutil")

try:
    #pip install PyQRCode
    import pyqrcode
except ImportError:
    _logger.warning('Cannot import pyqrcode library')

try:
    #sudo pip install pypng
    import png
except ImportError:
    _logger.warning('Cannot import png library')

try:
    import hashlib
except ImportError:
    _logger.warning('Cannot import hashlib library')

try:
    import base64
except ImportError:
    _logger.warning('Cannot import base64 library')

try:
    import textwrap
except:
    _logger.warning("no se ha cargado textwrap")

try:
    import gzip
except:
    _logger.warning("no se ha cargado gzip")

import zipfile
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

try:
    from suds.client import Client
except:
    _logger.warning("no se ha cargado suds")

server_url = {
    'HABILITACION':'https://facturaelectronica.dian.gov.co/habilitacion/B2BIntegrationEngine/FacturaElectronica/facturaElectronica.wsdl?',
    'PRODUCCION':'https://facturaelectronica.dian.gov.co/operacion/B2BIntegrationEngine/FacturaElectronica/facturaElectronica.wsdl?',
}


class DianDocument(models.Model):
    _name = 'dian.document'
    _rec_name = 'dian_code'

    document_id = fields.Many2one('account.invoice', string="Número de documento", readonly=True, required=True)
    state = fields.Selection([('por_notificar', 'Por notificar'), 
                            ('error', 'Error'), 
                            ('por_validar', 'Por validar'), 
                            ('exitoso', 'Exitoso'), 
                            ('rechazado', 'Rechazado')],
                            string="Estatus",
                            readonly=True,
                            default='por_notificar',
                            required=True)
    date_document_dian = fields.Datetime(string="Fecha envio al DIAN", readonly=True)
    shipping_response = fields.Selection([('100','100 Error al procesar la solicitud WS entrante'),
                                        ('101','101 El formato de los datos del ejemplar recibido no es correcto: Las entradas de directorio no están permitidos'),
                                        ('102','102 El formato de los datos del ejemplar recibido no es correcto: Tamaño de archivo comprimido zip es 0 o desconocido'), 
                                        ('103','103 Tamaño de archivo comprimido zip es 0 o desconocido'),
                                        ('104','104 Sólo un archivo es permitido por archivo Zip'), 
                                        ('200','200 Ejemplar recibido exitosamente pasará a verificación'),
                                        ('300','300 Archivo no soportado: Solo reconoce los tipos Invoice, DebitNote o CreditNote'),
                                        ('310','310 El ejemplar contiene errores de validación semantica'), 
                                        ('320','320 Parámetros de solicitud de servicio web, no coincide contra el archivo'),
                                        ('500','500 Error interno del servicio intentar nuevamente')],
                            string="Respuesta de envío",
                            readonly=True)
    response_document_dian = fields.Selection([('7200001','7200001 Recibida'),
                                            ('7200002','7200002 Existosa'),
                                            ('7200003','7200003 En proceso de validación'),
                                            ('7200004','7200004 Fallida (Documento no cumple 1 o más validaciones de DIAN)'),
                                            ('7200005','7200005 Error (El xml no es válido)')],
                            string="Respuesta documento DIAN",
                            readonly=True)
    dian_code = fields.Char(string='Código DIAN', readonly=True)
    xml_document = fields.Text(string='Contenido XML', readonly=True)
    xml_file_name = fields.Char(string='Nombre archivo xml', readonly=True)
    zip_file_name = fields.Char(string='Nombre archivo zip', readonly=True)
    date_request_dian = fields.Datetime(string="Fecha consulta DIAN", readonly=True)
    cufe = fields.Char(string='CUFE', readonly=True)
    QR_code = fields.Text(string='Código QR', readonly=True)
    PDF_document = fields.Binary(string='Documento PDF', readonly=True)
    date_email_send = fields.Datetime(string="Fecha envío email", readonly=True)
    date_email_acknowledgment = fields.Datetime(string="Fecha acuse email", readonly=True)
    response_message_dian = fields.Text(string="Mensaje de respuesta DIAN", readonly=True)
    last_shipping = fields.Boolean(string="Ultimo envío", default=True)
    customer_name = fields.Char(string="Cliente", readonly=True, related='document_id.partner_id.name')
    date_document = fields.Date(string="Fecha documento", readonly=True, related='document_id.date_invoice')
    customer_email = fields.Char(string="Email cliente", readonly=True, related='document_id.partner_id.email')
    document_type = fields.Selection([('f','Factura'), ('c','Nota/Credito'), ('d','Nota/Debito')], string="Tipo de documento", readonly=True)
    resend = fields.Boolean(string="Autorizar reenvio?", default=False)


    @api.multi
    def generate_new_dian_document(self):
        self.ensure_one()
        self.resend = False
        self.last_shipping = False
        vals = {'document_id' : self.document_id.id, 'document_type' : self.document_type}
        new_dian_document = self.create(vals)
        return new_dian_document


    @api.model
    def request_validating_dian(self):
        by_validate_docs = self.env['dian.document'].search([('state', '=', 'por_validar')])
        for by_validate_doc in by_validate_docs:
            dict_resp_dian = self._request_document_dian(by_validate_doc)
            by_validate_doc.date_request_dian = fields.Datetime.now()
            by_validate_doc.response_document_dian = dict_resp_dian['codigo']
            by_validate_doc.response_message_dian = dict_resp_dian['response_message_dian']

            if dict_resp_dian['codigo'] == '7200002':
                by_validate_doc.state = 'exitoso'
                # by_validate_doc.qr_code = self._generate_barcode_img(by_validate_doc)
                # by_validate_doc.pdf_document = self._generate_pdf_dian(by_validate_doc.qr_code)
                account_invoice = self.env['account.invoice'].search([('id', '=', by_validate_doc.document_id.id)])
                account_invoice.write({'diancode_id' : by_validate_doc.id})

            elif dict_resp_dian['codigo'] == '7200003':
                by_validate_doc.write({'state' : 'por_validar'})

            elif dict_resp_dian['codigo'] == '7200004':
                by_validate_doc.write({'state' : 'rechazado', 'resend' : True})

            elif dict_resp_dian['codigo'] == '7200005':
                by_validate_doc.write({'state' : 'rechazado', 'resend' : True})
        return True


    @api.model
    def _request_document_dian(self, por_validar):
        dict_response_dian = {}
        dict_response_dian['codigo'] = '7200002'
        dict_response_dian['response_message_dian'] = "CUFE verificado"
        return dict_response_dian


    @api.model
    def send_pending_dian(self):
        template_basic_data_xml = self._template_basic_data_xml()
        template_tax_data_xml = self._template_tax_data_xml()
        template_line_data_xml = self._template_line_data_xml()
        template_signature_data_xml = self._template_signature_data_xml()
        template_send_data_xml = self._template_send_data_xml()
        dian_constants = self._get_dian_constants()
        # Se obtienen los documento a enviar
        by_validate_invoices = self.env['dian.document'].search([('state', '=', 'por_notificar'),('document_type', '=', 'f')])
        by_validate_credit_notes = self.env['dian.document'].search([('state', '=', 'por_notificar'),('document_type', '=', 'c')])
        cn_with_validated_invoices_ids = []
        for by_validate_cn in by_validate_credit_notes:
            invoice_validated = self.env['account.invoice'].search([('move_name', '=', by_validate_cn.document_id.origin),('type', '=', 'out_invoice'),('diancode_id', '!=', False)])
            if invoice_validated:
                cn_with_validated_invoices_ids.append(by_validate_cn.id)
        by_validate_credit_notes_autorized = self.env['dian.document'].browse(cn_with_validated_invoices_ids)
        docs_send_dian = by_validate_invoices + by_validate_credit_notes_autorized
        #docs_send_dian = self.env['dian.document'].search([('state', '=', 'por_notificar'),('document_type', '=', 'f')])
        for doc_send_dian in docs_send_dian:
            # Datos de encabezado de la factura            
            data_header_doc = self.env['account.invoice'].search([('id', '=', doc_send_dian.document_id.id)])
            # Constantes del documento
            data_constants_document = self._generate_data_constants_document(data_header_doc)            
            # Detalle de impuestos
            data_taxs_xml = self._generate_taxs_data_xml(template_tax_data_xml, data_header_doc.id)
            # Detalle líneas de factura
            data_lines_xml = self._generate_lines_data_xml(template_line_data_xml, data_header_doc.id)
            # Generar CUFE
            CUFE = self._generate_cufe(data_header_doc.id, data_constants_document['InvoiceID'], data_constants_document['IssueDate'], 
                                    data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'],
                                    dian_constants['SupplierID'], data_constants_document['CustomerID'],
                                    data_constants_document['CustomerID'], dian_constants['TechnicalKey'])
            doc_send_dian.cufe = CUFE
            # Construye el documento XML sin firma
            data_xml_signature = ''
            data_xml_document = self._generate_data_document_xml(template_basic_data_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature)
            # Genera la firma en el documento xml
            data_xml_signature = self._generate_signature(data_xml_document, template_signature_data_xml)
            # Construye el documento XML con firma
            data_xml_document = self._generate_data_document_xml(template_basic_data_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature)
            # Generar nombre del archvio xml
            doc_send_dian.xml_file_name = self._generate_xml_filename()
            # Generar codigo DIAN
            doc_send_dian.dian_code = data_constants_document['InvoiceID']
            # Almacenar archivo xml
            doc_send_dian.xml_document = data_xml_document
            # Generar nombre archvio ZIP
            data_xml_document_zip = self._generate_zip_filename()
            # Comprimir documento electrónico         
            Document = self._generate_zip_content()
            #Fecha y hora de la petición
            Created = self._generate_datetime_created()
            # Construye el XML de petición o envío  
            data_xml_send = self._generate_data_send_xml(template_send_data_xml, dian_constants['Username'],
                                    dian_constants['Password'], dian_constants['NonceEncodingType'], Created,
                                    data_constants_document['CustomerID'], data_constants_document['InvoiceID'],
                                    data_constants_document['IssueDate'], Document)
            # Enviar documento al DIAN (Petición).
            data_xml_send = data_xml_document.replace('\n','')
            # print ''
            # print 'data_xml_document', data_xml_document 
            # print ''
            # client = Client(url=server_url['HABILITACION'])
            # response = client.service.EnvioFacturaElectronica(__inject={'msg' : data_xml_send})
            # Respuesta DIAN
            # print ''
            # print 'response', response 
            # print ''
            # # Generar documento PDF
            # doc_send_dian.PDF_document = self._

            doc_send_dian.state = 'por_validar'

            # Generar código QR
            # doc_send_dian.QR_code = self._generate_barcode_img(data_header_doc.id, data_constants_document['InvoiceID'], data_constants_document['IssueDate'], 
            #                         data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'], dian_constants['SupplierID'],
            #                         data_constants_document['CustomerID'], data_constants_document['PayableAmount'], CUFE)
        return 


    @api.model
    def _generate_signature(self, data_xml_document, template_signature_data_xml):
        data_xml_keyinfo_base = ''
        data_xml_politics = ''
        data_xml_SignedProperties_base = ''
        data_xml_SigningTime = ''
        # Generar clave de referencia 0 para la firma del documento (referencia ref0)
        data_xml_signature_ref_zero = self._generate_signature_ref0(data_xml_document)
        # Generar certficado publico para la firma del documento en el elemento keyinfo 
        data_public_certificate_base = self._generate_signature_public_certificate()
        # 1ra. Actualización de firma
        data_xml_signature = self._update_signature(template_signature_data_xml, data_xml_document, 
                                        data_xml_signature_ref_zero, data_public_certificate_base, 
                                        data_xml_keyinfo_base, data_xml_politics, 
                                        data_xml_SignedProperties_base, data_xml_SigningTime)
        # Generar clave de referencia 1 para la firma del documento (referencia keyinfo)
        data_xml_keyinfo_base = self._generate_signature_ref1(data_xml_signature)
        # Generar clave de politica de firma para la firma del documento (SigPolicyHash)
        data_xml_politics = self._generate_signature_politics(data_xml_signature)
        # Generar clave de referencia 2 para la firma del documento (referencia SignedProperties)
        data_xml_SignedProperties_base = self._generate_signature_ref2(data_xml_signature)
        # Obtener la hora de Colombia desde la hora del pc
        data_xml_SigningTime = self._generate_signature_signingtime()
        # 2da. y última actualización de firma 
        data_xml_signature = self._update_signature(template_signature_data_xml, data_xml_document, 
                                        data_xml_signature_ref_zero, data_public_certificate_base, 
                                        data_xml_keyinfo_base, data_xml_politics, 
                                        data_xml_SignedProperties_base, data_xml_SigningTime)
        return data_xml_signature


    @api.model
    def _get_dian_constants(self):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        partner = self.env['res.partner'].search([('id', '=', user.partner_id.id)])
        company = self.env['res.company'].search([('id', '=', user.company_id.id)])
        dian_constants = {}
        dian_constants['Username'] = '8ac82326-3016-430f-8d69-9efc4bcefd8f' 
        dian_constants['Password'] = '6361b7b5322acb07ced00a35a85a4cc5183da3a42ede0b07f578067a18425a55'
        dian_constants['InvoiceAuthorization'] = '2'                            # Número de resolución
        dian_constants['StartDate'] = '2018-08-23'                              # Fecha desde resolución
        dian_constants['EndDate'] = '2018-08-24'                                # Fecha hasta resolución
        dian_constants['Prefix'] = 'Prue'                                       # Prefijo de número de factura
        dian_constants['From'] = '1'                                            # Desde la secuencia
        dian_constants['To'] = '999'                                            # Hasta la secuencia
        dian_constants['TechnicalKey'] = '999'                                  # Clave técnica de la resolución de rango
        dian_constants['IdentificationCode'] = partner.country_id.code          # Identificador de pais
        dian_constants['ProviderID'] = partner.vat                              # ID Proveedor de software o cliente si es software propio
        dian_constants['SoftwareID'] = company.software_identification_code     # ID del software a utilizar
        dian_constants['SoftwareSecurityCode'] = self._generate_software_security_code(company.software_identification_code, company.software_pin) # Código de seguridad del software: (hashlib.new('sha384', str(self.company_id.software_id) + str(self.company_id.software_pin)))
        dian_constants['UBLVersionID'] = 'UBL 2.0'                              # Versión base de UBL usada. Debe marcar UBL 2.0
        dian_constants['ProfileID'] = 'DIAN 1.0'                                # Versión del Formato: Indicar versión del documento. Debe usarse "DIAN 1.0"
        dian_constants['SupplierAdditionalAccountID'] = '2'                     # Persona natural o jurídica (persona natural, jurídica, gran contribuyente, otros)
        dian_constants['SupplierID'] = partner.vat                              # Identificador fiscal: En Colombia, el NIT
        dian_constants['SupplierPartyName'] = partner.name                      # Nombre Comercial
        dian_constants['SupplierDepartment'] = ''                               # Estado o departamento (No requerido)
        dian_constants['SupplierCitySubdivisionName'] = ''                      # Cuidad, municipio o distrito (No requerido)
        dian_constants['SupplierCityName'] = partner.city                       # Municipio o ciudad
        dian_constants['SupplierLine'] = partner.street                         # Calle
        dian_constants['SupplierCountry'] = partner.country_id.code 
        dian_constants['SupplierTaxLevelCode'] = '0'                            # Régimen al que pertenece Debe referenciar a una lista de códigos con los por ejemplo: • Común • Simplificado • No aplica valores correspondientes
        dian_constants['SupplierRegistrationName'] = company.trade_name        # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        dian_constants['NonceEncodingType'] = self._generate_nonceencodingtype(company.seed_code) # semilla para generar números aleatorios
        return dian_constants


    def _template_basic_data_xml(self):
        template_basic_data_xml = """<fe:Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:clm54217="urn:un:unece:uncefact:codelist:specification:54217:2001" xmlns:clm66411="urn:un:unece:uncefact:codelist:specification:66411:2001" xmlns:clmIANAMIMEMediaType="urn:un:unece:uncefact:codelist:specification:IANAMIMEMediaType:2003" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:qdt="urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:udt="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xsi:schemaLocation="http://www.dian.gov.co/contratos/facturaelectronica/v1 http://www.dian.gov.co/micrositios/fac_electronica/documentos/XSD/r0/DIAN_UBL.xsd urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2 http://www.dian.gov.co/micrositios/fac_electronica/documentos/common/UnqualifiedDataTypeSchemaModule-2.0.xsd urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2 http://www.dian.gov.co/micrositios/fac_electronica/documentos/common/UBL-QualifiedDatatypes-2.0.xsd">
    <ext:UBLExtensions>
        <ext:UBLExtension>
            <ext:ExtensionContent>
                <sts:DianExtensions>
                    <sts:InvoiceControl>
                        <sts:InvoiceAuthorization>%(InvoiceAuthorization)s</sts:InvoiceAuthorization>
                        <sts:AuthorizationPeriod>
                            <cbc:StartDate>%(StartDate)s</cbc:StartDate>
                            <cbc:EndDate>%(EndDate)s</cbc:EndDate>
                        </sts:AuthorizationPeriod>
                        <sts:AuthorizedInvoices>
                            <sts:Prefix>%(Prefix)s</sts:Prefix>
                            <sts:From>%(From)s</sts:From>
                            <sts:To>%(To)s</sts:To>
                        </sts:AuthorizedInvoices>
                    </sts:InvoiceControl>
                    <sts:InvoiceSource>
                        <cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.0">%(IdentificationCode)s</cbc:IdentificationCode>
                    </sts:InvoiceSource>
                    <sts:SoftwareProvider>
                        <sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">%(ProviderID)s</sts:ProviderID>
                        <sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">%(SoftwareID)s</sts:SoftwareID>
                    </sts:SoftwareProvider>
                    <sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">%(SoftwareSecurityCode)s</sts:SoftwareSecurityCode>
                </sts:DianExtensions>
            </ext:ExtensionContent>
        </ext:UBLExtension>
        <ext:UBLExtension>
            <ext:ExtensionContent>%(data_xml_signature)s
            </ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>
    <cbc:UBLVersionID>%(UBLVersionID)s</cbc:UBLVersionID>
    <cbc:ProfileID>%(ProfileID)s</cbc:ProfileID>
    <cbc:ID>%(InvoiceID)s</cbc:ID>
    <cbc:UUID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">%(UUID)s</cbc:UUID>
    <cbc:IssueDate>%(IssueDate)s</cbc:IssueDate>
    <cbc:IssueTime>%(IssueTime)s</cbc:IssueTime>
    <cbc:InvoiceTypeCode listAgencyID="195" listAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" listSchemeURI="http://www.dian.gov.co/contratos/facturaelectronica/v1/InvoiceType">%(InvoiceTypeCode)s</cbc:InvoiceTypeCode>
    <cbc:Note></cbc:Note>
    <cbc:DocumentCurrencyCode>%(DocumentCurrencyCode)s</cbc:DocumentCurrencyCode>
    <fe:AccountingSupplierParty>
        <cbc:AdditionalAccountID>%(SupplierAdditionalAccountID)s</cbc:AdditionalAccountID>
        <fe:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="31">%(SupplierID)s</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyName>
                <cbc:Name>%(SupplierPartyName)s</cbc:Name>
            </cac:PartyName>
            <fe:PhysicalLocation>
                <fe:Address>
                    <cbc:Department>%(SupplierDepartment)s</cbc:Department>
                    <cbc:CitySubdivisionName>%(SupplierCitySubdivisionName)s</cbc:CitySubdivisionName>
                    <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
                    <cac:AddressLine>
                        <cbc:Line>%(SupplierLine)s</cbc:Line>
                    </cac:AddressLine>
                    <cac:Country>
                        <cbc:IdentificationCode>%(SupplierCountry)s</cbc:IdentificationCode>
                    </cac:Country>
                </fe:Address>
            </fe:PhysicalLocation>
            <fe:PartyTaxScheme>
                <cbc:TaxLevelCode>%(SupplierTaxLevelCode)s</cbc:TaxLevelCode>
                <cac:TaxScheme/>
            </fe:PartyTaxScheme>
            <fe:PartyLegalEntity>
                <cbc:RegistrationName>%(SupplierRegistrationName)s</cbc:RegistrationName>
            </fe:PartyLegalEntity>
        </fe:Party>
    </fe:AccountingSupplierParty>
    <fe:AccountingCustomerParty>
        <cbc:AdditionalAccountID>%(CustomerAdditionalAccountID)s</cbc:AdditionalAccountID>
        <fe:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="31">%(CustomerID)s</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyName>
                <cbc:Name>%(CustomerPartyName)s</cbc:Name>
            </cac:PartyName>
            <fe:PhysicalLocation>
                <fe:Address>
                    <cbc:Department>%(CustomerDepartment)s</cbc:Department>
                    <cbc:CitySubdivisionName>%(CustomerCitySubdivisionName)s</cbc:CitySubdivisionName>
                    <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
                    <cac:AddressLine>
                        <cbc:Line>%(CustomerAddressLine)s</cbc:Line>
                    </cac:AddressLine>
                    <cac:Country>
                        <cbc:IdentificationCode>%(CustomerCountry)s</cbc:IdentificationCode>
                    </cac:Country>
                </fe:Address>
            </fe:PhysicalLocation>
            <fe:PartyTaxScheme>
                <cbc:TaxLevelCode>%(TaxLevelCode)s</cbc:TaxLevelCode>
                <cac:TaxScheme/>
            </fe:PartyTaxScheme>
            <fe:PartyLegalEntity>
                <cbc:RegistrationName>%(RegistrationName)s</cbc:RegistrationName>
            </fe:PartyLegalEntity>
        </fe:Party>
    </fe:AccountingCustomerParty>%(data_taxs_xml)s
    <fe:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="COP">%(TotalLineExtensionAmount)s</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="COP">%(TotalTaxExclusiveAmount)s</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">0.00</cbc:TaxInclusiveAmount>
        <cbc:AllowanceTotalAmount currencyID="COP">0.00</cbc:AllowanceTotalAmount>
        <cbc:ChargeTotalAmount currencyID="COP">0.00</cbc:ChargeTotalAmount>
        <cbc:PrepaidAmount currencyID="COP">0.00</cbc:PrepaidAmount>
        <cbc:PayableAmount currencyID="COP">%(PayableAmount)s</cbc:PayableAmount>
    </fe:LegalMonetaryTotal>%(data_lines_xml)s
</fe:Invoice>""" 
        return template_basic_data_xml


    def _template_tax_data_xml(self):
        template_tax_data_xml = """ 
    <fe:TaxTotal>
        <cbc:TaxAmount currencyID="COP">%(TaxTotalTaxAmount)s</cbc:TaxAmount>
        <cbc:TaxEvidenceIndicator>%(TaxTotalTaxEvidenceIndicator)s</cbc:TaxEvidenceIndicator>
        <fe:TaxSubtotal>
            <cbc:TaxableAmount currencyID="COP">%(TaxTotalTaxableAmount)s</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="COP">%(TaxTotalTaxAmount)s</cbc:TaxAmount>
            <cbc:Percent>%(TaxTotalPercent)s</cbc:Percent>
            <cac:TaxCategory>
                <cac:TaxScheme>
                    <cbc:ID>%(TaxTotalTaxSchemeID)s</cbc:ID>
                </cac:TaxScheme>
            </cac:TaxCategory>
        </fe:TaxSubtotal>
    </fe:TaxTotal>"""
        return template_tax_data_xml


    def _template_line_data_xml(self):
        template_line_data_xml = """
    <fe:InvoiceLine>
        <cbc:ID>%(ILLinea)s</cbc:ID>
        <cbc:InvoicedQuantity>%(ILInvoicedQuantity)s</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="COP">%(ILLineExtensionAmount)s</cbc:LineExtensionAmount>
        <cac:AllowanceCharge>
            <cbc:ChargeIndicator>%(ILChargeIndicator)s</cbc:ChargeIndicator>
            <cbc:Amount currencyID="COP">%(ILAmount)s</cbc:Amount>
        </cac:AllowanceCharge>
        <fe:Item>
            <cbc:Description>%(ILDescription)s</cbc:Description>
        </fe:Item>
        <fe:Price>
            <cbc:PriceAmount currencyID="COP">%(ILPriceAmount)s</cbc:PriceAmount>
        </fe:Price>
    </fe:InvoiceLine>""" 
        return template_line_data_xml


    def _template_signature_data_xml(self):
        template_signature_data_xml = """
                <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5">
                    <ds:SignedInfo>
                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                        <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
                        <ds:Reference Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-ref0" URI="">
                            <ds:Transforms>
                                <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                            </ds:Transforms>
                            <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                            <ds:DigestValue>%(data_xml_signature_ref_zero)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference URI="#xmldsig-87d128b5-aa31-4f0b-8e45-3d9cfa0eec26-keyinfo">
                            <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                            <ds:DigestValue>%(data_xml_keyinfo_base)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-signedprops">
                            <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                            <ds:DigestValue>%(data_xml_SignedProperties_base)s</ds:DigestValue>
                        </ds:Reference>
                    </ds:SignedInfo>
                    <ds:SignatureValue Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-sigvalue">
                    </ds:SignatureValue>
                    <ds:KeyInfo Id="xmldsig-87d128b5-aa31-4f0b-8e45-3d9cfa0eec26-keyinfo">
                        <ds:X509Data>
                            <ds:X509Certificate>%(data_public_certificate_base)s</ds:X509Certificate>
                        </ds:X509Data>
                    </ds:KeyInfo>
                    <ds:Object>
                        <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5">
                            <xades:SignedProperties Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-signedprops">
                                <xades:SignedSignatureProperties>
                                    <xades:SigningTime>%(data_xml_SigningTime)s</xades:SigningTime>
                                    <xades:SigningCertificate>
                                        <xades:Cert>
                                            <xades:CertDigest>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                                                <ds:DigestValue></ds:DigestValue>
                                            </xades:CertDigest>
                                            <xades:IssuerSerial>
                                                <ds:X509IssuerName>C=CO,L=Bogota D.C.,O=Andes SCD.,OU=Division de certificacion entidad final,CN=CA ANDES SCD S.A. Clase II,1.2.840.113549.1.9.1=#1614696e666f40616e6465737363642e636f6d2e636f</ds:X509IssuerName>
                                                <ds:X509SerialNumber>9128602840918470673</ds:X509SerialNumber>
                                            </xades:IssuerSerial>
                                        </xades:Cert>
                                        <xades:Cert>
                                            <xades:CertDigest>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                                                <ds:DigestValue>YGJTXnOzmebG2Mc6A/QapNi1PRA=</ds:DigestValue>
                                            </xades:CertDigest>
                                            <xades:IssuerSerial>
                                                <ds:X509IssuerName>C=CO,L=Bogota D.C.,O=Andes SCD,OU=Division de certificacion,CN=ROOT CA ANDES SCD S.A.,1.2.840.113549.1.9.1=#1614696e666f40616e6465737363642e636f6d2e636f</ds:X509IssuerName>
                                                <ds:X509SerialNumber>7958418607150926283</ds:X509SerialNumber>
                                            </xades:IssuerSerial>
                                        </xades:Cert>
                                        <xades:Cert>
                                            <xades:CertDigest>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                                                <ds:DigestValue>6EVr7OINyc49AgvNkie19xul55c=</ds:DigestValue>
                                            </xades:CertDigest>
                                            <xades:IssuerSerial>
                                                <ds:X509IssuerName>C=CO,L=Bogota D.C.,O=Andes SCD,OU=Division de certificacion,CN=ROOT CA ANDES SCD S.A.,1.2.840.113549.1.9.1=#1614696e666f40616e6465737363642e636f6d2e636f</ds:X509IssuerName>
                                                <ds:X509SerialNumber>3248112716520923666</ds:X509SerialNumber>
                                            </xades:IssuerSerial>
                                        </xades:Cert>
                                    </xades:SigningCertificate>
                                    <xades:SignaturePolicyIdentifier>
                                        <xades:SignaturePolicyId>
                                            <xades:SigPolicyId>
                                                <xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
                                            </xades:SigPolicyId>
                                            <xades:SigPolicyHash>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                                                <ds:DigestValue>%(data_xml_politics)s</ds:DigestValue>
                                            </xades:SigPolicyHash>
                                        </xades:SignaturePolicyId>
                                    </xades:SignaturePolicyIdentifier>
                                    <xades:SignerRole>
                                        <xades:ClaimedRoles>
                                            <xades:ClaimedRole>supplier</xades:ClaimedRole>
                                        </xades:ClaimedRoles>
                                    </xades:SignerRole>
                                </xades:SignedSignatureProperties>
                            </xades:SignedProperties>
                        </xades:QualifyingProperties>
                    </ds:Object>
                </ds:Signature>""" 
        return template_signature_data_xml 

    def _template_send_data_xml(self):
        template_send_data_xml = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:rep="http://www.dian.gov.co/servicios/facturaelectronica/ReportarFactura">
<soapenv:Header>
<wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
<wsse:UsernameToken>
<wsse:Username>%(Username)s</wsse:Username>
<wsse:Password>%(Password)s</wsse:Password>
<wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">%(NonceEncodingType)s</wsse:Nonce>
<wsu:Created>%(Created)s</wsu:Created>
</wsse:UsernameToken>
</wsse:Security>
</soapenv:Header>
<soapenv:Body>
<rep:EnvioFacturaElectronicaPeticion>
<rep:NIT>%(NIT)s</rep:NIT>
<rep:InvoiceNumber>%(InvoiceNumber)s</rep:InvoiceNumber>
<rep:IssueDate>%(IssueDate)s</rep:IssueDate>
<rep:Document>%(Document)s</rep:Document>
</rep:EnvioFacturaElectronicaPeticion>
</soapenv:Body>
</soapenv:Envelope>"""
        return template_send_data_xml


    def _generate_data_constants_document(self, data_header_doc):
        data_constants_document = {}
        data_constants_document['LineExtensionAmount'] = data_header_doc.amount_untaxed        # Total Importe bruto antes de impuestos: Total importe bruto, suma de los importes brutos de las líneas de la factura.
        data_constants_document['TaxExclusiveAmount'] = data_header_doc.amount_untaxed         # Total Base Imponible (Importe Bruto+Cargos-Descuentos): Base imponible para el cálculo de los impuestos
        data_constants_document['PayableAmount'] = data_header_doc.amount_total                # Total de Factura: Total importe bruto + Total Impuestos-Total Impuesto Retenidos
        data_constants_document['IssueDate'] = data_header_doc.date_invoice                    # Fecha de emisión de la factura a efectos fiscales        
        data_constants_document['IssueTime'] = self._get_time()                                # Hora de emisión de la fcatura
        data_constants_document['InvoiceTypeCode'] = self._get_doctype(data_header_doc.type)   # Tipo de Factura, código: facturas de venta, y transcripciones; tipo = 1 para factura de venta
        data_constants_document['DocumentCurrencyCode'] = data_header_doc.currency_id.name     # Divisa de la Factura
        data_constants_document['InvoiceID'] = self._generate_dian_code() # Número de documento dian
        data_constants_document['CustomerAdditionalAccountID'] = '2' if data_header_doc.partner_id.is_company else '1' # Persona natural o jurídica
        data_constants_document['CustomerID'] = data_header_doc.partner_id.vat                 # Identificador fiscal: En Colombia, el NIT
        data_constants_document['CustomerPartyName'] = data_header_doc.partner_id.name         # Nombre Comercial
    #--0CustomerDepartment = 'PJ - 800199436 - Adquiriente FE'
        data_constants_document['CustomerDepartment'] = ''
    #--0CustomerCitySubdivisionName = 'PJ - 800199436 - Adquiriente FE'
        data_constants_document['CustomerCitySubdivisionName'] = ''
        data_constants_document['CustomerCityName'] = data_header_doc.partner_id.city
        data_constants_document['CustomerCountry'] = data_header_doc.partner_id.country_id.name
        data_constants_document['CustomerAddressLine'] = data_header_doc.partner_id.street
    #--1TaxLevelCode = '0'  # Régimen al que pertenece Debe referenciar a una lista de códigos con los por ejemplo: • Común • Simplificado • No aplica valores correspondientes
        data_constants_document['TaxLevelCode'] = '0'
    #--1RegistrationName = 'PJ - 800199436' # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        data_constants_document['RegistrationName'] = 'Desarrollo de software'
        return data_constants_document


    @api.model
    def _generate_taxs_data_xml(self, template_tax_data_xml, invoice_id):
        data_tax_xml = ''
        data_tax_detail_doc = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice_id)])
        for item_tax in data_tax_detail_doc:
            tax_percentage = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)])
            invoice_lines = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id), ('invoice_line_tax_ids', 'in', item_tax.tax_id.id)])
            total_base = 0.00
            for invoice_line in invoice_lines:
                total_base += total_base + invoice_line.price_subtotal
            TaxTotalTaxAmount = str(item_tax.amount)                                      # Importe Impuesto (detalle): Importe del impuesto retenido
            TaxTotalTaxEvidenceIndicator = 'false' if item_tax.amount == 0.00 else 'true' # Indica que el elemento es un Impuesto retenido (7.1.1) y no un impuesto (8.1.1) True
            TaxTotalTaxableAmount = str(total_base)                                       # 7.1.1.1 / 8.1.1.1 - Base Imponible: Base Imponible sobre la que se calcula la retención de impuesto
            TaxTotalPercent = str(tax_percentage.amount)                                  # 7.1.1.3 / 8.1.1.3 - Porcentaje: Porcentaje a aplicar
            #--1TaxTotalTaxSchemeID = '0'                                                 # Código de impuesto
            TaxTotalTaxSchemeID = '0'
            data_tax_xml += template_tax_data_xml % {'TaxTotalTaxAmount' : TaxTotalTaxAmount,
                                                    'TaxTotalTaxEvidenceIndicator' : TaxTotalTaxEvidenceIndicator,
                                                    'TaxTotalTaxableAmount' : TaxTotalTaxableAmount,
                                                    'TaxTotalPercent' : TaxTotalPercent,
                                                    'TaxTotalTaxSchemeID' : TaxTotalTaxSchemeID,
                                                    }
        return data_tax_xml


    def _generate_lines_data_xml(self, template_line_data_xml,invoice_id):
        ILLinea = 0
        data_line_xml = ''
        data_lines_doc = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)])
        for data_line in data_lines_doc:
            ILLinea += 1
            ILInvoicedQuantity = data_line.quantity          # 13.1.1.9 - Cantidad: Cantidad del artículo solicitado. Número de unidades servidas/prestadas.
            ILLineExtensionAmount = data_line.price_subtotal # 13.1.1.12 - Costo Total: Coste Total. Resultado: Unidad de Medida x Precio Unidad.
            ILChargeIndicator = 'true'
            ILAmount =  data_line.discount                   # Valor Descuento: Importe total a descontar.
            ILDescription = data_line.name
            ILPriceAmount = data_line.price_unit             # Precio Unitario   
            data_line_xml += template_line_data_xml % {'ILLinea' : ILLinea,
                                                    'ILInvoicedQuantity' : ILInvoicedQuantity,
                                                    'ILLineExtensionAmount' : ILLineExtensionAmount,
                                                    'ILAmount' : ILAmount,
                                                    'ILDescription' : ILDescription,
                                                    'ILPriceAmount' : ILPriceAmount,
                                                    'ILChargeIndicator' : ILChargeIndicator,
                                                    }
        return data_line_xml


    @api.model
    def _generate_cufe(self, invoice_id, NumFac, FecFac, Time, ValFac, NitOFE, TipAdq, NumAdq, ClTec):
        #NumFac = '323200000129'
        FecFac = FecFac.replace('-','')+Time.replace(':','')
        ValFac = str(ValFac)
        #ValFac = '1109376.00'
        # Obtine los distintos impuestos
        data_tax_detail_doc = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice_id)])
        type_tax_amount = [0,0,0]
        total_tax_amount = 0
        line = 0
        for item_tax in data_tax_detail_doc:
            line += 1
            type_tax_amount[line] = item_tax.amount 
            total_tax_amount += item_tax.amount 
        #CodImp1 = '01'
        #ValImp1 = '0.00'
        #CodImp2 = '02'
        #ValImp2 = '45928.16'
        #CodImp3 = '03'
        #ValImp3 = '107165.72'
        #ValImp = '1296705.20'
        CodImp1 = '01' 
        ValImp1 = str(type_tax_amount[1]) if line > 1 else '0.00'
        CodImp2 = '02'
        ValImp2 = str(type_tax_amount[2]) if line >= 2 else '0.00'
        CodImp3 = '03'
        ValImp3 = str(type_tax_amount[3]) if line == 3 else '0.00'
        ValImp =  str(total_tax_amount)
        #NitOFE = '700085371'
        #TipAdq = '31' # Puede ser el NIT del cliente
        #NumAdq = '800199436'
        #ClTec = '693ff6f2a553c3646a063436fd4dd9ded0311471' # falta
        CUFE = hashlib.sha1(NumFac + FecFac + ValFac + CodImp1 + ValImp1 + CodImp2 + ValImp2 + CodImp3 + ValImp3 + ValImp + NitOFE + TipAdq + NumAdq + ClTec)
        CUFE = CUFE.hexdigest()
        return CUFE


    def _generate_data_document_xml(self, template_basic_data_xml, dc, dcd, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature):
        template_basic_data_xml = template_basic_data_xml % {'InvoiceAuthorization' : dc['InvoiceAuthorization'],
                        'StartDate' : dc['StartDate'],
                        'EndDate' : dc['EndDate'],
                        'Prefix' : dc['Prefix'],
                        'From' : dc['From'],
                        'To' : dc['To'],
                        'IdentificationCode' : dc['IdentificationCode'],
                        'ProviderID' : dc['ProviderID'],
                        'SoftwareID' : dc['SoftwareID'],
                        'SoftwareSecurityCode' : dc['SoftwareSecurityCode'],
                        'LineExtensionAmount' : dcd['LineExtensionAmount'],
                        'TaxExclusiveAmount' : dcd['TaxExclusiveAmount'],
                        'PayableAmount' : dcd['PayableAmount'],
                        'UBLVersionID' : dc['UBLVersionID'],
                        'ProfileID' : dc['ProfileID'],
                        'InvoiceID' : dcd['InvoiceID'],
                        'UUID' : CUFE,
                        'IssueDate' : dcd['IssueDate'],
                        'IssueTime' : dcd['IssueTime'],
                        'InvoiceTypeCode' : dcd['InvoiceTypeCode'],
                        'DocumentCurrencyCode' : dcd['DocumentCurrencyCode'],
                        'SupplierAdditionalAccountID' : dc['SupplierAdditionalAccountID'],
                        'SupplierID' : dc['SupplierID'],
                        'SupplierPartyName' : dc['SupplierPartyName'],
                        'SupplierDepartment' : dc['SupplierDepartment'],
                        'SupplierCitySubdivisionName' : dc['SupplierCitySubdivisionName'],
                        'SupplierCityName' : dc['SupplierCityName'],
                        'SupplierLine' : dc['SupplierLine'],
                        'SupplierCountry' : dc['SupplierCountry'],
                        'SupplierTaxLevelCode' : dc['SupplierTaxLevelCode'],
                        'SupplierRegistrationName' : dc['SupplierRegistrationName'],
                        'CustomerAdditionalAccountID' : dcd['CustomerAdditionalAccountID'],
                        'CustomerID' : dcd['CustomerID'],
                        'CustomerPartyName' : dcd['CustomerPartyName'],
                        'CustomerDepartment' : dcd['CustomerDepartment'],
                        'CustomerCitySubdivisionName' : dcd['CustomerCitySubdivisionName'],
                        'CustomerCityName' : dcd['CustomerCityName'],
                        'CustomerCountry' : dcd['CustomerCountry'],
                        'CustomerAddressLine' : dcd['CustomerAddressLine'],                                
                        'TaxLevelCode' : dcd['TaxLevelCode'],
                        'RegistrationName' : dcd['RegistrationName'],
                        'TotalLineExtensionAmount' : dcd['LineExtensionAmount'],
                        'TotalTaxExclusiveAmount' : dcd['TaxExclusiveAmount'],
                        'data_taxs_xml' : data_taxs_xml,
                        'data_lines_xml' : data_lines_xml,
                        'data_xml_signature' : data_xml_signature,
                        }
        return template_basic_data_xml


    @api.model
    def _generate_data_send_xml(self, template_send_data_xml, Username, Password, NonceEncodingType, Created, 
                                CustomerID, InvoiceID, IssueDate, Document):
        data_send_xml = template_send_data_xml % {'Username' : Username,
                        'Password' : Password,
                        'NonceEncodingType' : NonceEncodingType,
                        'Created' : Created,
                        'NIT' : CustomerID,
                        'InvoiceNumber' : InvoiceID,
                        'IssueDate' : IssueDate,
                        'Document' : Document,
                        }
        return data_send_xml


    @api.model
    def _generate_signature_ref0(self, data_xml_document):
        # 1er paso generar la referencia 0 que consiste en obtener keyvalue desde todo el xml del documento
        #          electronico aplicando el algoritmo SHA1 y convirtiendolo a base64
        data_xml_c14n = etree.tostring(etree.fromstring(data_xml_document), method="c14n")
        data_xml_sha1 = hashlib.new('sha1', data_xml_c14n)
        data_xml_digest = data_xml_sha1.digest()
        data_xml_signature_ref0 = base64.b64encode(data_xml_digest)
        return data_xml_signature_ref0


    @api.model
    def _generate_signature_public_certificate(self):  
        # falta obtener certificado público  
        data_certificado_publico = "7482-mdsghs-bdgd75-bdgetsbdn-25362-dgdndns-dgwrsbs-846324bsfs"
        data_certificado_publico_base = base64.b64encode(data_certificado_publico)
        return data_certificado_publico_base


    @api.model
    def _update_signature(self, template_signature_data_xml, data_xml_document, 
                                data_xml_signature_ref_zero, data_public_certificate_base, 
                                data_xml_keyinfo_base, data_xml_politics, 
                                data_xml_SignedProperties_base, data_xml_SigningTime):
        data_xml_signature = template_signature_data_xml % {'data_xml_signature_ref_zero' : data_xml_signature_ref_zero,                                        
                                        'data_public_certificate_base' : data_public_certificate_base,
                                        'data_xml_keyinfo_base' : data_xml_keyinfo_base,
                                        'data_xml_politics' : data_xml_politics,
                                        'data_xml_SignedProperties_base' : data_xml_SignedProperties_base,
                                        'data_xml_SigningTime' : data_xml_SigningTime,                                                    
                                        }
        return data_xml_signature


    @api.multi
    def _generate_signature_ref1(self, data_xml_signature):
        # Generar la referencia 1 que consiste en obtener keyvalue desde el keyinfo contenido 
        # en el documento electrónico aplicando el algoritmo SHA1 y convirtiendolo a base64
        data_xml_keyinfo = etree.fromstring(data_xml_signature)
        element_xml_keyinfo = etree.tostring(data_xml_keyinfo[2])
        data_xml_keyinfo_c14n = etree.tostring(etree.fromstring(element_xml_keyinfo), method="c14n")
        data_xml_keyinfo_sha1 = hashlib.new('sha1', data_xml_keyinfo_c14n)
        data_xml_keyinfo_digest = data_xml_keyinfo_sha1.digest()
        data_xml_keyinfo_base = base64.b64encode(data_xml_keyinfo_digest)
        return data_xml_keyinfo_base


    @api.multi
    def _generate_signature_politics(self, data_xml_signature):
        # Paso generar la referencia 2 que consiste en obtener keyvalue desde el documento de 
        # politica aplicando el algoritmo SHA1 y convirtiendolo a base64. Se  puede  utilizar  
        # como una constante ya que no variará en años segun lo indica la DIAN.
        #  
        #politicav2 = '/home/odoo/Instancias/9.0/politicadefirmav2.pdf'
        #politicav2 = open(politicav2,'r')
        #contenido_politicav2 = politicav2.read()
        #politicav2_sha1 = hashlib.new('sha1', contenido_politicav2)
        #politicav2_digest = politicav2_sha1.digest()
        #politicav2_base = base64.b64encode(politicav2_digest)
        data_xml_politics = 'sbcECQ7v+y/m3OcBCJyvmkBhtFs='
        return data_xml_politics


    @api.multi
    def _generate_signature_ref2(self, template_signature_data_xml):
        # Generar la referencia 2, se obtine desde el elemento SignedProperties que se 
        # encuentra en la firma aplicando el algoritmo SHA1 y convirtiendolo a base64.
        data_xml_SignedProperties = etree.fromstring(template_signature_data_xml)
        data_xml_SignedProperties = etree.tostring(data_xml_SignedProperties[3])
        data_xml_SignedProperties = etree.fromstring(data_xml_SignedProperties)
        data_xml_SignedProperties = etree.tostring(data_xml_SignedProperties[0])
        data_xml_SignedProperties = etree.fromstring(data_xml_SignedProperties)
        data_xml_SignedProperties = etree.tostring(data_xml_SignedProperties[0])
        data_xml_SignedProperties_c14n = etree.tostring(etree.fromstring(data_xml_SignedProperties), method="c14n")
        data_xml_SignedProperties_sha1 = hashlib.new('sha1', data_xml_SignedProperties_c14n)
        data_xml_SignedProperties_digest = data_xml_SignedProperties_sha1.digest()
        data_xml_SignedProperties_base = base64.b64encode(data_xml_SignedProperties_digest)
        return data_xml_SignedProperties_base


    @api.multi
    def _generate_signature_signingtime(self):
        fmt = "%Y-%m-%dT%H:%M:%S+02"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        data_xml_SigningTime = now_bogota.strftime(fmt)
        return data_xml_SigningTime


    def _generate_dian_code(self):
        dian_code = 'PRUE0001'
        return dian_code


    @api.model
    def _get_doctype(self, doctype):
        if doctype == 'out_invoice':
            docdian = '1'
        elif doctype == 'out_refund':
            docdian = '2'
        else:
            docdian = '3'
        return docdian


    @api.model
    def _get_time(self):
        fmt = "%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        now_time = now_bogota.strftime(fmt)
        return now_time


    def _generate_xml_filename(self):
        return True


    def _generate_zip_filename(self):
        return True


    def _generate_zip_content(self):
        # Falta definir directorio donde se graben los archivos zip
        # Obtener nombre del archvio zip
        zf = zipfile.ZipFile('/home/odoo/Instancias/9.0/face_f0000002.zip', mode="w")
        try:
            zf.write('/home/odoo/Instancias/9.0/face_f0000002.xml', compress_type=compression)
        finally:
            zf.close()
        data_xml_b64 = '/home/odoo/Instancias/9.0/face_f0000002.zip'
        data_xml_b64 = open(data_xml_b64,'r')
        contenido_data_xml_b64 = data_xml_b64.read()
        data_xml_b64 = base64.b64encode(contenido_data_xml_b64)
        return data_xml_b64


    @api.model
    def _generate_barcode_img(self, invoice_id, NumFac, FecFac, Time, ValFac, NitOFE, DocAdq,  ValFacIm, CUFE):
        FecFac = FecFac.replace('-','')+Time.replace(':','')
        ValOtroIm = 00.00 # Falta
        # Obtine impuestos
        total_tax_amount = 0
        data_tax_detail_doc = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice_id)])
        for item_tax in data_tax_detail_doc:
            total_tax_amount += item_tax.amount
        ValIva = total_tax_amount    
        datos_qr = ' NumFac: '+NumFac+' FecFac: '+FecFac+' NitFac: '+NitOFE+' DocAdq: '+DocAdq+' ValFac: '+str(ValFac)+' ValIva: '+str(ValIva)+' ValOtroIm: '+str(ValOtroIm)+' ValFacIm: '+str(ValFacIm)+' CUFE: '+CUFE
        print ''
        print 'datos_qr: ', datos_qr
        print ''

#         texto = '''NumFac: A02F-00117836
# FecFac: 20140319105605
# NitFac: 808183133 
# DocAdq: 8081972684
# ValFac: 1000.00
# ValIva: 160.00
# ValOtroIm: 0.00
# ValFacIm: 1160.00
# CUFE: 2836a15058e90baabbf6bf2e97f05564ea0324a6'''

        # Genera código QR
        qr_code = pyqrcode.create(datos_qr)
        print ''
        print 'qr_code: ', qr_code
        print ''
        img_as_str_qr = qr_code.png_as_base64_str(scale=5)
        print ''
        print 'img_as_str: ', img_as_str_qr
        print ''        
        # Genera el archivo png
        qr_code.png('qr-invoice.png')
        return img_as_str_qr


    @api.model
    def _generate_nonceencodingtype(self, seed_code):
        # NonceEncodingType # Se obtiene de 1. Calcular un valor aleatorio cuya semilla será definida y solamante conocida por el facturador electrónico y 2. Convertir a Base 64 el valor aleatorio obtenbido.
        # Falta calcular número aleatorio
        nonceencodingtype = base64.b64encode(seed_code)
        return nonceencodingtype


    def _generate_software_security_code(self, software_identification_code, software_pin):
        software_security_code = hashlib.sha384(software_identification_code + software_pin)
        software_security_code = software_security_code.hexdigest()
        return  software_security_code 


    def _generate_datetime_created(self):
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        Created = now_bogota.strftime(fmt)[:-3]+'Z'
        return Created