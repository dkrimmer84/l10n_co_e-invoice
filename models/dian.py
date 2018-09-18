# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import *

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
    def _get_resolution_dian(self):
        rec_dian_sequence = self.env['ir.sequence'].search([('use_dian_control', '=', True),('active', '=', True)])
        if not rec_dian_sequence:
            raise ValidationError('No se pueden generar documento para la DIAN porque no hay secuenciador DIAN activo.')
        rec_active_resolution = self.env['ir.sequence.dian_resolution'].search([('sequence_id', '=', rec_dian_sequence.id),('active_resolution', '=', True)])
        if not rec_active_resolution:
            raise ValidationError('No se puede generar documento para la DIAN porque no hay rango de resolucion DIAN activo.')
 
        dict_resolution_dian = {}
        dict_resolution_dian['Prefix'] = rec_dian_sequence.prefix                               # Prefijo de número de factura
        dict_resolution_dian['InvoiceAuthorization'] = rec_active_resolution.resolution_number  # Número de resolución
        dict_resolution_dian['StartDate'] = rec_active_resolution.date_from                   # Fecha desde resolución
        dict_resolution_dian['EndDate'] = rec_active_resolution.date_to                       # Fecha hasta resolución
        dict_resolution_dian['From'] = rec_active_resolution.number_from                        # Desde la secuencia
        dict_resolution_dian['To'] = rec_active_resolution.number_to                            # Hasta la secuencia
        dict_resolution_dian['TechnicalKey'] = rec_active_resolution.technical_key              # Clave técnica de la resolución de rango
        dict_resolution_dian['InvoiceID'] = rec_dian_sequence.next_by_id()                      # Codigo del documento
        return dict_resolution_dian


    @api.model
    def request_validating_dian(self):
        dict_dian_constants = self._get_dian_constants()
        by_validate_docs = self.env['dian.document'].search([('state', '=', 'por_validar')])
        for by_validate_doc in by_validate_docs:
            dict_resp_dian = self._request_document_dian_soap(by_validate_doc, dict_dian_constants)

            by_validate_doc.date_request_dian = fields.Datetime.now()
            by_validate_doc.response_document_dian = dict_resp_dian['codigo']
            by_validate_doc.response_message_dian = dict_resp_dian['response_message_dian']

            if dict_resp_dian['codigo'] == '7200002':
                by_validate_doc.state = 'exitoso'
                # by_validate_doc.pdf_document = self._generate_pdf_dian(by_validate_doc.qr_code)
                account_invoice = self.env['account.invoice'].search([('id', '=', by_validate_doc.document_id.id)])
                account_invoice.write({'diancode_id' : by_validate_doc.id})

            elif dict_resp_dian['codigo'] == '7200003':
                by_validate_doc.write({'state' : 'por_validar'})

            elif dict_resp_dian['codigo'] == '7200004':
                by_validate_doc.write({'state' : 'rechazado', 'resend' : True})

            elif dict_resp_dian['codigo'] == '7200005':
                by_validate_doc.write({'state' : 'por_validar', 'resend' : False})
        return True



    @api.model
    def _request_document_dian_soap(self, by_validate_doc, dict_dian_constants):
        xml_soap_request_validating_dian = self._generate_xml_soap_request_validating_dian(by_validate_doc, dict_dian_constants)
        print '\nxml_soap_request_validating_dian ', xml_soap_request_validating_dian
        dict_response_dian = {}
        dict_response_dian['codigo'] = '7200002'
        dict_response_dian['response_message_dian'] = "CUFE verificado"
        return dict_response_dian



    @api.model
    def _request_document_dian(self, por_validar):
            # sequence_id = self.env['ir.sequence'].search([('dian', '=', True)])
            # next_dian_code = self.env['ir.sequence'].search([('dian', '=', True)]).next_by_id(sequence_id.id)
            # rec_sequence_date_range = self.env['ir.sequence.date_range'].search([('sequence_id', '=', sequence_id)])
            # TechnicalKey = rec_sequence_date_range.technical_key

            # print '\n\nnext_dian_code:', next_dian_code
            # print '\n\nTechnicalKey:', TechnicalKey
            # prueba
            
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
            data_constants_document = self._generate_data_constants_document(data_header_doc, dian_constants['NitSinDV'])            
            # Detalle de impuestos
            data_taxs = self._get_taxs_data(data_header_doc.id)
            data_taxs_xml = self._generate_taxs_data_xml(template_tax_data_xml, data_taxs)
            # Detalle líneas de factura
            data_lines_xml = self._generate_lines_data_xml(template_line_data_xml, data_header_doc.id)
            # Generar CUFE
            CUFE = self._generate_cufe(data_header_doc.id, data_constants_document['InvoiceID'], data_constants_document['IssueDate'], 
                                    data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'],
                                    dian_constants['SupplierID'], data_constants_document['CustomerSchemeID'],
                                    data_constants_document['CustomerID'], data_constants_document['TechnicalKey'], data_constants_document['PayableAmount'], data_taxs)
            doc_send_dian.cufe = CUFE
            # Construye el documento XML sin firma
            data_xml_signature = ''
            data_xml_document = self._generate_data_document_xml(template_basic_data_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature)
            # Genera la firma en el documento xml
            data_xml_signature = self._generate_signature(data_xml_document, template_signature_data_xml, dian_constants['Certificate'])
            # Construye el documento XML con firma
            data_xml_document = self._generate_data_document_xml(template_basic_data_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature)
            # Generar codigo DIAN
            doc_send_dian.dian_code = data_constants_document['InvoiceID']
            # Generar nombre del archvio xml
            doc_send_dian.xml_file_name = data_constants_document['FileNameXLM']
            # Almacenar archivo xml
            doc_send_dian.xml_document = data_xml_document
            # Generar nombre archvio ZIP
            doc_send_dian.zip_file_name = data_constants_document['FileNameZIP']
            # Comprimir documento electrónico         
            Document = self._generate_zip_content(data_constants_document['FileNameXLM'], data_constants_document['FileNameZIP'], data_xml_document)
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
            doc_send_dian.QR_code = self._generate_barcode(data_constants_document['InvoiceID'], data_constants_document['IssueDate'], 
                                    data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'], dian_constants['SupplierID'],
                                    data_constants_document['CustomerID'], data_constants_document['PayableAmount'], CUFE, data_taxs)
        # return 


    @api.model
    def _generate_signature(self, data_xml_document, template_signature_data_xml, certificate):
        data_xml_keyinfo_base = ''
        data_xml_politics = ''
        data_xml_SignedProperties_base = ''
        data_xml_SigningTime = ''
        # Generar clave de referencia 0 para la firma del documento (referencia ref0)
        data_xml_signature_ref_zero = self._generate_signature_ref0(data_xml_document)
        # Generar certficado publico para la firma del documento en el elemento keyinfo 
        data_public_certificate_base = base64.b64encode(certificate)
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
        # rango_resolution = self.env['res.company'].search([('id', '=', user.company_id.id)])
        dian_constants = {}
        dian_constants['Username'] = company.software_identification_code       # Identificador del software en estado en pruebas o activo 
        dian_constants['Password'] = hashlib.sha256(company.software_pin)       # Es el resultado de aplicar la función de resumen SHA-256 sobre la contraseña del software en estado en pruebas o activo
        dian_constants['Password'] = dian_constants['Password'].hexdigest() 
        dian_constants['IdentificationCode'] = partner.country_id.code          # Identificador de pais
        dian_constants['ProviderID'] = partner.formatedNit.replace('.','').replace('-','') if partner.formatedNit else '' # ID Proveedor de software o cliente si es software propio
        dian_constants['SoftwareID'] = company.software_identification_code     # ID del software a utilizar
        dian_constants['SoftwareSecurityCode'] = self._generate_software_security_code(company.software_identification_code, company.software_pin) # Código de seguridad del software: (hashlib.new('sha384', str(self.company_id.software_id) + str(self.company_id.software_pin)))
        dian_constants['UBLVersionID'] = 'UBL 2.0'                              # Versión base de UBL usada. Debe marcar UBL 2.0
        dian_constants['ProfileID'] = 'DIAN 1.0'                                # Versión del Formato: Indicar versión del documento. Debe usarse "DIAN 1.0"
        dian_constants['SupplierAdditionalAccountID'] = '2' if partner.company_type == 'company' else '1' # Persona natural o jurídica (persona natural, jurídica, gran contribuyente, otros)
        dian_constants['SupplierID'] = partner.formatedNit.replace('.','').replace('-','') if partner.formatedNit else '' # Identificador fiscal: En Colombia, el NIT
        dian_constants['SupplierSchemeID'] = partner.doctype
        dian_constants['SupplierPartyName'] = partner.name                      # Nombre Comercial
        dian_constants['SupplierDepartment'] = partner.state_id.name            # Estado o departamento (No requerido)
        dian_constants['SupplierCitySubdivisionName'] = partner.xcity.name      # Cuidad, municipio o distrito (No requerido)
        dian_constants['SupplierCityName'] = partner.city                       # Municipio o ciudad
        dian_constants['SupplierLine'] = partner.street                         # Calle
        dian_constants['SupplierCountry'] = partner.country_id.code 
        dian_constants['SupplierTaxLevelCode'] = partner.x_pn_retri             # Régimen al que pertenece Debe referenciar a una lista de códigos con los por ejemplo: • Común • Simplificado • No aplica valores correspondientes
        dian_constants['SupplierRegistrationName'] = company.trade_name         # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        dian_constants['NonceEncodingType'] = self._generate_nonceencodingtype(company.seed_code) # semilla para generar números aleatorios
        dian_constants['Certificate'] = company.digital_certificate             # KeyInfo: a partir del certificado público convirtiendolo a base64
        dian_constants['NitSinDV'] = partner.xidentification                    # Nit sin digito validador
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
                <cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="%(SupplierSchemeID)s">%(SupplierID)s</cbc:ID>
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
                <cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerSchemeID)s">%(CustomerID)s</cbc:ID>
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


    def _generate_data_constants_document(self, data_header_doc, NitSinDV):
        data_constants_document = {}
        data_resolution  = self._get_resolution_dian()
        # Generar nombre del archvio xml
        data_constants_document['FileNameXLM'] = self._generate_xml_filename(data_resolution, NitSinDV, data_header_doc.type)
        # Generar Id de Signature
        # FileNameXLM = hashlib.new('sha256', data_constants_document['FileNameXLM'])
        # FileNameXLM = FileNameXLM.digest()
        # FileNameXLM = base64.b64encode(FileNameXLM)
        # print ''
        # print 'FileNameXLM', data_constants_document['FileNameXLM']
        # print 'FileNameXLM base64', FileNameXLM
        # print ''

        data_constants_document['FileNameZIP'] = self._generate_zip_filename(data_resolution, NitSinDV, data_header_doc.type)
        data_constants_document['InvoiceAuthorization'] = data_resolution['InvoiceAuthorization']  # Número de resolución
        data_constants_document['StartDate'] = data_resolution['StartDate']                        # Fecha desde resolución
        data_constants_document['EndDate'] = data_resolution['EndDate']                            # Fecha hasta resolución
        data_constants_document['Prefix'] = data_resolution['Prefix']                              # Prefijo de número de factura
        data_constants_document['From'] = data_resolution['From']                                  # Desde la secuencia
        data_constants_document['To'] = data_resolution['To']                                      # Hasta la secuencia
        data_constants_document['InvoiceID'] = data_resolution['InvoiceID']                        # Número de documento dian
        data_constants_document['TechnicalKey'] = data_resolution['TechnicalKey']                  # Clave técnica de la resolución de rango
        data_constants_document['LineExtensionAmount'] = data_header_doc.amount_untaxed         # Total Importe bruto antes de impuestos: Total importe bruto, suma de los importes brutos de las líneas de la factura.
        data_constants_document['TaxExclusiveAmount'] = data_header_doc.amount_untaxed          # Total Base Imponible (Importe Bruto+Cargos-Descuentos): Base imponible para el cálculo de los impuestos
        data_constants_document['PayableAmount'] = data_header_doc.amount_total                 # Total de Factura: Total importe bruto + Total Impuestos-Total Impuesto Retenidos
        data_constants_document['IssueDate'] = data_header_doc.date_invoice                     # Fecha de emisión de la factura a efectos fiscales        
        data_constants_document['IssueTime'] = self._get_time()                                 # Hora de emisión de la fcatura
        data_constants_document['InvoiceTypeCode'] = self._get_doctype(data_header_doc.type)    # Tipo de Factura, código: facturas de venta, y transcripciones; tipo = 1 para factura de venta
        data_constants_document['DocumentCurrencyCode'] = data_header_doc.currency_id.name      # Divisa de la Factura
        data_constants_document['CustomerAdditionalAccountID'] = '2' if data_header_doc.partner_id.company_type == 'company' else '1'
        data_constants_document['CustomerID'] = data_header_doc.partner_id.formatedNit.replace('.','').replace('-','') if data_header_doc.partner_id.formatedNit else ''# Identificador fiscal: En Colombia, el NIT
        data_constants_document['CustomerSchemeID'] = data_header_doc.partner_id.doctype                # tipo de identificdor fiscal 
        data_constants_document['CustomerPartyName'] = data_header_doc.partner_id.name          # Nombre Comercial
    #--0CustomerDepartment = 'PJ - 800199436 - Adquiriente FE'
        data_constants_document['CustomerDepartment'] = data_header_doc.partner_id.state_id.name
    #--0CustomerCitySubdivisionName = 'PJ - 800199436 - Adquiriente FE'
        data_constants_document['CustomerCitySubdivisionName'] = data_header_doc.partner_id.xcity.name
        data_constants_document['CustomerCityName'] = data_header_doc.partner_id.city
        data_constants_document['CustomerCountry'] = data_header_doc.partner_id.country_id.name
        data_constants_document['CustomerAddressLine'] = data_header_doc.partner_id.street
    #--1TaxLevelCode = '0'  # Régimen al que pertenece Debe referenciar a una lista de códigos con los por ejemplo: • Común • Simplificado • No aplica valores correspondientes
        data_constants_document['TaxLevelCode'] = data_header_doc.partner_id.x_pn_retri
    #--1RegistrationName = 'PJ - 800199436' # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        data_constants_document['RegistrationName'] = data_header_doc.partner_id.companyName
        return data_constants_document


    @api.model
    def _get_taxs_data(self, invoice_id):
        dic_taxs_data = {}
        iva_01 = 0.00
        ico_02 = 0.00 
        ica_03 = 0.00
        tax_percentage_iva_01 = 0.00
        tax_percentage_ico_02 = 0.00
        tax_percentage_ica_03 = 0.00
        total_base_iva_01 = 0.00
        total_base_ico_02 = 0.00
        total_base_ica_03 = 0.00
        data_tax_detail_doc = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice_id)])
        for item_tax in data_tax_detail_doc:
            iva_01 += item_tax.amount if data_tax_detail_doc.tax_id.tax_group_id.id  == 5 else 0 
            ica_03 += item_tax.amount if data_tax_detail_doc.tax_id.tax_group_id.id  == 4 else 0 
            ico_02 += item_tax.amount if data_tax_detail_doc.tax_id.tax_group_id.id  not in (5,4) else 0  
            tax_percentage_iva_01 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if data_tax_detail_doc.tax_id.tax_group_id.id  == 5 else tax_percentage_iva_01
            tax_percentage_ica_03 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if data_tax_detail_doc.tax_id.tax_group_id.id  == 4 else tax_percentage_ico_02
            tax_percentage_ico_02 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if data_tax_detail_doc.tax_id.tax_group_id.id  not in (5,4) else tax_percentage_ica_03
            invoice_lines = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id), ('invoice_line_tax_ids', 'in', item_tax.tax_id.id)])
            for invoice_line in invoice_lines:
                total_base_iva_01 += invoice_line.price_subtotal if data_tax_detail_doc.tax_id.tax_group_id.id  == 5 else 0
                total_base_ica_03 += invoice_line.price_subtotal if data_tax_detail_doc.tax_id.tax_group_id.id  == 4 else 0
                total_base_ico_02 += invoice_line.price_subtotal if data_tax_detail_doc.tax_id.tax_group_id.id  not in (5,4) else 0
        dic_taxs_data['iva_01'] = iva_01
        dic_taxs_data['tax_percentage_iva_01'] = tax_percentage_iva_01
        dic_taxs_data['total_base_iva_01'] = total_base_iva_01
        dic_taxs_data['ica_03'] = ica_03
        dic_taxs_data['tax_percentage_ica_03'] = tax_percentage_ica_03
        dic_taxs_data['total_base_ica_03'] = total_base_ica_03
        dic_taxs_data['ico_02'] = ico_02
        dic_taxs_data['tax_percentage_ico_02'] = tax_percentage_ico_02
        dic_taxs_data['total_base_ico_02'] = total_base_ico_02
        return dic_taxs_data


    @api.model
    def _generate_taxs_data_xml(self, template_tax_data_xml, data_taxs):
        data_tax_xml = ''
        # iva_01
        TaxTotalTaxAmount = str(data_taxs['iva_01'])                                         # Importe Impuesto (detalle): Importe del impuesto retenido
        TaxTotalTaxEvidenceIndicator = 'false' if data_taxs['iva_01'] == 0.00 else 'true'    # Indica que el elemento es un Impuesto retenido (7.1.1) y no un impuesto (8.1.1) True
        TaxTotalTaxableAmount = str(data_taxs['total_base_iva_01'])                          # 7.1.1.1 / 8.1.1.1 - Base Imponible: Base Imponible sobre la que se calcula la retención de impuesto
        TaxTotalPercent = str(data_taxs['tax_percentage_iva_01'])                            # 7.1.1.3 / 8.1.1.3 - Porcentaje: Porcentaje a aplicar
        TaxTotalTaxSchemeID = '01'                                              # 7.1.1.2 - Tipo: Tipo o clase impuesto. Concepto fiscal por el que se tributa. Debería si un campo que referencia a una lista de códigos. En la lista deberían aparecer los impuestos estatales o nacionales. Código de impuesto
        data_tax_xml += template_tax_data_xml % {'TaxTotalTaxAmount' : TaxTotalTaxAmount,
                                                'TaxTotalTaxEvidenceIndicator' : TaxTotalTaxEvidenceIndicator,
                                                'TaxTotalTaxableAmount' : TaxTotalTaxableAmount,
                                                'TaxTotalPercent' : TaxTotalPercent,
                                                'TaxTotalTaxSchemeID' : TaxTotalTaxSchemeID,
                                                }
        # ico_02
        TaxTotalTaxAmount = str(data_taxs['ico_02'])                                         # Importe Impuesto (detalle): Importe del impuesto retenido
        TaxTotalTaxEvidenceIndicator = 'false' if data_taxs['ico_02'] == 0.00 else 'true'          # Indica que el elemento es un Impuesto retenido (7.1.1) y no un impuesto (8.1.1) True
        TaxTotalTaxableAmount = str(data_taxs['total_base_ico_02'])                          # 7.1.1.1 / 8.1.1.1 - Base Imponible: Base Imponible sobre la que se calcula la retención de impuesto
        TaxTotalPercent = str(data_taxs['tax_percentage_ico_02'])                            # 7.1.1.3 / 8.1.1.3 - Porcentaje: Porcentaje a aplicar
        TaxTotalTaxSchemeID = '02'                                                           # 7.1.1.2 - Tipo: Tipo o clase impuesto. Concepto fiscal por el que se tributa. Debería si un campo que referencia a una lista de códigos. En la lista deberían aparecer los impuestos estatales o nacionales. Código de impuesto
        data_tax_xml += template_tax_data_xml % {'TaxTotalTaxAmount' : TaxTotalTaxAmount,
                                                'TaxTotalTaxEvidenceIndicator' : TaxTotalTaxEvidenceIndicator,
                                                'TaxTotalTaxableAmount' : TaxTotalTaxableAmount,
                                                'TaxTotalPercent' : TaxTotalPercent,
                                                'TaxTotalTaxSchemeID' : TaxTotalTaxSchemeID,
                                                }

        # ica_03
        TaxTotalTaxAmount = str(data_taxs['ica_03'])                                         # Importe Impuesto (detalle): Importe del impuesto retenido
        TaxTotalTaxEvidenceIndicator = 'false' if data_taxs['ica_03'] == 0.00 else 'true'          # Indica que el elemento es un Impuesto retenido (7.1.1) y no un impuesto (8.1.1) True
        TaxTotalTaxableAmount = str(data_taxs['total_base_ica_03'])                          # 7.1.1.1 / 8.1.1.1 - Base Imponible: Base Imponible sobre la que se calcula la retención de impuesto
        TaxTotalPercent = str(data_taxs['tax_percentage_ica_03'])                            # 7.1.1.3 / 8.1.1.3 - Porcentaje: Porcentaje a aplicar
        TaxTotalTaxSchemeID = '03'                                                           # 7.1.1.2 - Tipo: Tipo o clase impuesto. Concepto fiscal por el que se tributa. Debería si un campo que referencia a una lista de códigos. En la lista deberían aparecer los impuestos estatales o nacionales. Código de impuesto
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
            ILChargeIndicator = 'true'                       # Indica que el elemento es un Cargo (5.1.1) y no un descuento (4.1.1)
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
    def _generate_cufe(self, invoice_id, NumFac, FecFac, Time, ValFac, NitOFE, TipAdq, NumAdq, ClTec, ValPag, data_taxs):
        FecFac = FecFac.replace('-','')+Time.replace(':','')
        ValFac = str(ValFac)
        # Obtine los distintos impuestos
        data_tax_detail_doc = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice_id)])
        CodImp1 = '01' 
        ValImp1 = str(data_taxs['iva_01'])
        CodImp2 = '02'
        ValImp2 = str(data_taxs['ico_02'])
        CodImp3 = '03'
        ValImp3 = str(data_taxs['ica_03'])
        ValPag  = str(ValPag)
        TipAdq  = str(TipAdq)
        CUFE = hashlib.sha1(NumFac +';'+ FecFac +';'+ ValFac +';'+ CodImp1 +';'+ ValImp1 +';'+ CodImp2 +';'+ ValImp2 +';'+ CodImp3 +';'+ ValImp3 +';'+ ValPag +';'+ NitOFE +';'+ TipAdq +';'+ NumAdq +';'+ ClTec)
        CUFE = CUFE.hexdigest()
        return CUFE


    def _generate_data_document_xml(self, template_basic_data_xml, dc, dcd, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature):
        template_basic_data_xml = template_basic_data_xml % {'InvoiceAuthorization' : dcd['InvoiceAuthorization'],
                        'StartDate' : dcd['StartDate'],
                        'EndDate' : dcd['EndDate'],
                        'Prefix' : dcd['Prefix'],
                        'From' : dcd['From'],
                        'To' : dcd['To'],
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
                        'SupplierSchemeID' : dc['SupplierSchemeID'],
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
                        'CustomerSchemeID' : dcd['CustomerSchemeID'],
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
        fmt = "%Y-%m-%dT%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc.astimezone(timezone('America/Bogota')) + relativedelta(seconds=+2)
        data_xml_SigningTime = now_bogota.strftime(fmt) 
        return data_xml_SigningTime


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

    
    @api.model
    def _generate_xml_filename(self, data_resolution, NitSinDV, doctype):
        if doctype == 'out_invoice':
            docdian = 'face_f'
        elif doctype == 'out_refund':
            docdian = 'face_c'
        else:
            docdian = 'face_d'
        nit = NitSinDV.zfill(10)
        len_prefix = len(data_resolution['Prefix'])
        len_invoice = len(data_resolution['InvoiceID'])
        dian_code_int = int(data_resolution['InvoiceID'][len_prefix:len_invoice])
        dian_code_hex = self.IntToHex(dian_code_int)
        dian_code_hex.zfill(10)
        file_name_xml = docdian + NitSinDV.zfill(10) + dian_code_hex.zfill(10) + '.xml'
        return file_name_xml


    def IntToHex(self, dian_code_int):
        dian_code_hex = '%02x' % dian_code_int
        return dian_code_hex


    def _generate_zip_filename(self, data_resolution, NitSinDV, doctype):
        if doctype == 'out_invoice':
            docdian = 'ws_f'
        elif doctype == 'out_refund':
            docdian = 'ws_c'
        else:
            docdian = 'ws_d'
        nit = NitSinDV.zfill(10)
        len_prefix = len(data_resolution['Prefix'])
        len_invoice = len(data_resolution['InvoiceID'])
        dian_code_int = int(data_resolution['InvoiceID'][len_prefix:len_invoice])
        dian_code_hex = self.IntToHex(dian_code_int)
        dian_code_hex.zfill(10)
        file_name_zip = docdian + NitSinDV.zfill(10) + dian_code_hex.zfill(10) + '.zip'
        print ''
        print 'file_name_zip: ', file_name_zip
        print ''
        return file_name_zip


    def _generate_zip_content(self, FileNameXML, FileNameZIP, data_xml_document):
        # Falta definir directorio donde se graben los archivos zip
        # Almacena archvio XML
        xml_file = '/home/odoo/Instancias/9.0/' + FileNameXML
        f = open (xml_file,'w')
        f.write(data_xml_document)
        f.close()
        # Comprime archvio XML
        zip_file = '/home/odoo/Instancias/9.0/' + FileNameZIP
        zf = zipfile.ZipFile(zip_file, mode="w")
        try:
            zf.write(xml_file, compress_type=compression)
        finally:
            zf.close()
        # Obtiene datos comprimidos
        data_xml_b64 = zip_file
        data_xml_b64 = open(data_xml_b64,'r')
        contenido_data_xml_b64 = data_xml_b64.read()
        return data_xml_b64


    @api.model
    def _generate_barcode(self, NumFac, FecFac, Time, ValFac, NitOFE, DocAdq,  ValFacIm, CUFE, data_taxs):
        FecFac = FecFac.replace('-','')+Time.replace(':','')
        ValIva = data_taxs['iva_01'] 
        ValOtroIm = data_taxs['ico_02'] + data_taxs['ica_03']   
        datos_qr = ' NumFac: '+NumFac+' FecFac: '+FecFac+' NitFac: '+NitOFE+' DocAdq: '+DocAdq+' ValFac: '+str(ValFac)+' ValIva: '+str(ValIva)+' ValOtroIm: '+str(ValOtroIm)+' ValFacIm: '+str(ValFacIm)+' CUFE: '+CUFE
        # Genera código QR
        qr_code = pyqrcode.create(datos_qr)
        qr_code = qr_code.png_as_base64_str(scale=5)
        # Genera el archivo png
        # qr_code.png('qr-invoice.png')
        return qr_code


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


    def _generate_xml_soap_request_validating_dian(self, by_validate_doc, dict_dian_constants):
        UserName = dict_dian_constants['UserName']
        Password = dict_dian_constants['Password']
        NitEmisor = dict_dian_constants['SupplierID']
        IdentificadorSoftware = dict_dian_constants['SoftwareID']
        if by_validate_doc.tipo_documento == 'f':
            TipoDocumento = '1'
        elif by_validate_doc.tipo_documento == 'd':
            TipoDocumento = '2'
        else:
            TipoDocumento = '3'
        NumeroDocumento = by_validate_doc.dian_code
        FechaGeneracion = by_validate_doc.date_document.strftime("%Y-%m-%dT%H:%M:%S") 
        CUFE = by_validate_doc.cufe
        template_xml_soap_request_validating_dian = """
            <soapenv:Header>
            <wsse:Security
            xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
            xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsse:UsernameToken>
            <wsse:Username>%(UserName)s</wsse:Username>
            <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-
            profile-1.0#PasswordText">%(Password)s
            </wsse:Password>
            </wsse:UsernameToken>
            </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
            <con:ConsultaResultadoValidacionDocumentosPeticion>
            <con:TipoDocumento>%(TipoDocumento)s</con:TipoDocumento>
            <con:NumeroDocumento>%(NumeroDocumento)s</con:NumeroDocumento>
            <con:NitEmisor>%(NitEmisor)s</con:NitEmisor>
            <con:FechaGeneracion>%(FechaGeneracion)s</con:FechaGeneracion>
            <con:IdentificadorSoftware>%(IdentificadorSoftware)s</con:IdentificadorSoftware>
            <con:CUFE>%(CUFE)s</con:CUFE>
            </con:ConsultaResultadoValidacionDocumentosPeticion>
            </soapenv:Body>
"""

        print "template_xml_soap_request_validating_dian:", template_xml_soap_request_validating_dian

        xml_soap_request_validating_dian = template_xml_soap_request_validating_dian % {
                                        'UserName' : UserName,
                                        'Password' : Password,
                                        'TipoDocumento' : TipoDocumento,
                                        'NumeroDocumento' : NumeroDocumento,
                                        'NitEmisor' : NitEmisor,
                                        'FechaGeneracion' : FechaGeneracion,
                                        'IdentificadorSoftware' : IdentificadorSoftware,
                                        'CUFE' : CUFE}

        return xml_soap_request_validating_dian
