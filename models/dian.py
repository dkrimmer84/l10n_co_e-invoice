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

# from lxml.etree import Element, SubElement
from openerp.tools.translate import _

# try:
#     import shutil
# except:
#     print("Cannot import shutil")

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

from enum import Enum
# try:
#     from suds.client import Client
# except:
#     _logger.warning("no se ha cargado suds")

# try:
#     from suds import byte_str
# except:    
#     _logger.warning("no se ha cargado suds")


from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import OpenSSL
from OpenSSL import crypto
type_ = crypto.FILETYPE_PEM


from random import randint

# try:
#     from suds.sax.element import Element
# except:    
#     _logger.warning("no se ha cargado suds.sax.element")

# try:
#     from suds.sax.attribute import Attribute
# except:    
#     _logger.warning("no se ha cargado suds.sax.atribute")

try:
    import requests 
except:    
    _logger.warning("no se ha cargado requests")

try:
    import xmltodict
except ImportError:
    _logger.warning('Cannot import xmltodict library')
            
server_url = {
    'HABILITACION':'https://facturaelectronica.dian.gov.co/habilitacion/B2BIntegrationEngine/FacturaElectronica/facturaElectronica.wsdl',
    'PRODUCCION':'https://facturaelectronica.dian.gov.co/operacion/B2BIntegrationEngine/FacturaElectronica/facturaElectronica.wsdl',
    'HABILITACION_CONSULTA':'https://facturaelectronica.dian.gov.co/habilitacion/B2BIntegrationEngine/FacturaElectronica/consultaDocumentos.wsdl',
    'PRODUCCION_CONSULTA':'https://facturaelectronica.dian.gov.co/operacion/B2BIntegrationEngine/FacturaElectronica/consultaDocumentos.wsdl' 
}

import os
#USING_PYTHON2 = True if sys.version_info < (3, 0) else False
#xsdpath = os.path.dirname(os.path.realpath(__file__)).replace('/models','/static/xsd/')

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
    date_document_dian = fields.Char(string="Fecha envio al DIAN", readonly=True)
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
    transaction_code = fields.Integer(string='Código de la Transacción de validación', readonly=True)
    transaction_description = fields.Char(string='Descripción de la transacción de validación', readonly=True)
    response_document_dian = fields.Selection([('7200001','7200001 Recibida'),
                                            ('7200002','7200002 Exitosa'),
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
    QR_code = fields.Binary(string='Código QR', readonly=True)
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
        # Falta preguntar si con un mismo número de resolución DIAN se puede generar consecutivos de facturas
        # notas de débto y crédito. 
        rec_dian_sequence = self.env['ir.sequence'].search([('use_dian_control', '=', True),('active', '=', True),('sequence_dian_type', '=', 'invoice_computer_generated')])
        if not rec_dian_sequence:
            raise ValidationError('No se pueden generar documentos para la DIAN porque no hay secuenciador DIAN activo.')
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
            try:
                dict_response_dian = self._request_document_dian_soap(by_validate_doc, dict_dian_constants)
            except:
                print '\n\n\n'
                print("No existe comunicación con la DIAN")
                return
            #dict_response_dian = self._request_document_dian_soap(by_validate_doc, dict_dian_constants)
            if dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:CodigoTransaccion'] != '300':            
                print 'paso a'
                by_validate_doc.response_document_dian = dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:DocumentoRecibido']['ns3:DatosBasicosDocumento']['ns3:EstadoDocumento']
                by_validate_doc.transaction_code = dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:CodigoTransaccion']
                #dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:DocumentoRecibido']['ns3:DatosBasicosDocumento']['ns3:EstadoDocumento']
                by_validate_doc.transaction_description = dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:DescripcionTransaccion']
                #dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:DocumentoRecibido']['ns3:DatosBasicosDocumento']['ns3:DescripcionEstado']
                by_validate_doc.date_request_dian = fields.Datetime.now()
                message = by_validate_doc.response_message_dian
                for comment in dict_response_dian['xmlDocTree'].iter():
                    if comment.tag == "{http://www.dian.gov.co/servicios/facturaelectronica/ConsultaDocumentos}CodigoVeriFunc":
                        message += comment.text + ' '
                    if comment.tag == "{http://www.dian.gov.co/servicios/facturaelectronica/ConsultaDocumentos}DescripcionVeriFunc":
                        message += comment.text +  '\n'
                by_validate_doc.response_message_dian = message
                if dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:DocumentoRecibido']['ns3:DatosBasicosDocumento']['ns3:EstadoDocumento'] == '7200002':
                    print 'paso b'
                    account_invoice = self.env['account.invoice'].search([('id', '=', by_validate_doc.document_id.id)])
                    account_invoice.write({'diancode_id' : by_validate_doc.id})
                    plantilla_correo = self.env.ref('l10n_co_e-invoice.email_template_edi_invoice_dian', False)
                    plantilla_correo.send_mail(by_validate_doc.document_id.id, force_send = True)
                    by_validate_doc.date_email_send = fields.Datetime.now()
                    by_validate_doc.write({'state' : 'exitoso', 'resend' : False})
                else:
                    print 'paso c'
                    if dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:DocumentoRecibido']['ns3:DatosBasicosDocumento']['ns3:EstadoDocumento'] in  ('7200001','7200003'):
                        print 'paso d'
                        by_validate_doc.write({'state' : 'por_validar', 'resend' : False})
                    elif dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:DocumentoRecibido']['ns3:DatosBasicosDocumento']['ns3:EstadoDocumento'] == '7200004':
                        print 'paso e'
                        #by_validate_doc.write({'state' : 'rechazado', 'resend' : True})
                    elif dict_response_dian['dict_response_dian']['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns3:ConsultaResultadoValidacionDocumentosRespuesta']['ns3:DocumentoRecibido']['ns3:DatosBasicosDocumento']['ns3:EstadoDocumento'] == '7200005':
                        print 'paso f'
                        by_validate_doc.write({'state' : 'error', 'resend' : True})
                print 'paso g'


        #Mikel    
        # dict_dian_constants = self._get_dian_constants()
        # by_validate_docs = self.env['dian.document'].search([('state', '=', 'por_validar')])
        # for by_validate_doc in by_validate_docs:
        #     dict_response_dian = self._request_document_dian_soap(by_validate_doc, dict_dian_constants)
        #     by_validate_doc.date_request_dian = fields.Datetime.now()
        #     by_validate_doc.transaction_code = dict_response_dian['transaction_code']
        #     by_validate_doc.transaction_description = dict_response_dian['transaction_description']
        #     if dict_response_dian['transaction_code'] != 300:
        #         by_validate_doc.response_document_dian = dict_response_dian['response_document_dian']
        #         by_validate_doc.response_message_dian = dict_response_dian['response_message_dian']
        #         if dict_response_dian['response_document_dian'] == '7200002':
        #             by_validate_doc.state = 'exitoso'
        #             account_invoice = self.env['account.invoice'].search([('id', '=', by_validate_doc.document_id.id)])
        #             account_invoice.write({'diancode_id' : by_validate_doc.id})
        #             plantilla_correo = self.env.ref('l10n_co_e-invoice.email_template_edi_invoice_dian', False)
        #             plantilla_correo.send_mail(by_validate_doc.document_id.id, force_send = True)
        #             by_validate_doc.date_email_send = fields.Datetime.now()

        #         elif dict_response_dian['response_document_dian'] == '7200003':
        #             by_validate_doc.write({'state' : 'por_validar'})

        #         elif dict_response_dian['response_document_dian'] == '7200004':
        #             by_validate_doc.write({'state' : 'rechazado', 'resend' : True})

        #         elif dict_response_dian['response_document_dian'] == '7200005':
        #             by_validate_doc.write({'state' : 'por_validar', 'resend' : False})
        return True


    @api.model
    def _request_document_dian_soap(self, by_validate_doc, dict_dian_constants):
        xml_soap_request_validating_dian = self._generate_xml_soap_request_validating_dian(by_validate_doc, dict_dian_constants)
        xml_soap_request_validating_dian = '<?xml version="1.0" encoding="UTF-8"?>' + xml_soap_request_validating_dian
        xml_soap_request_validating_dian = xml_soap_request_validating_dian.replace('\n','')
        # Solicitar consulta de resultado
        headers = {'content-type': 'text/xml'} 
        response = requests.post(server_url['HABILITACION_CONSULTA'],data=xml_soap_request_validating_dian,headers=headers) 
        # Almacena respuesta DIAN en archvio temporal en disco
        xml_file_response_validate = dict_dian_constants['document_repository'] + '/' + 'validate_' + 'falta' 
        f = open(xml_file_response_validate,'w')
        f.write(response.content)
        f.close()
        # Obtiene solo la estructura xml y elimina archivo
        f = open(xml_file_response_validate,'r')
        line_xml_response = f.readline()
        while line_xml_response != '':
            if line_xml_response.find("<SOAP-ENV:Envelope") == 0:
                response_xml =  line_xml_response
            line_xml_response = f.readline()
        f.close()
        os.remove(xml_file_response_validate)

        dict_response_dian = xmltodict.parse(response_xml)
        xmlDocTree = etree.fromstring(response_xml)
        xmlDocTree = etree.tostring(xmlDocTree[1])
        xmlDocTree = etree.fromstring(xmlDocTree)
        xmlDocTree = etree.tostring(xmlDocTree[0])
        xmlDocTree = etree.fromstring(xmlDocTree)
        xmlDocTree = etree.tostring(xmlDocTree[3])
        xmlDocTree = etree.fromstring(xmlDocTree)
        xmlDocTree = etree.tostring(xmlDocTree[1])
        xmlDocTree = etree.fromstring(xmlDocTree)

        ResponseValidate = {}
        ResponseValidate['dict_response_dian'] = dict_response_dian
        ResponseValidate['xmlDocTree'] = xmlDocTree
        return ResponseValidate


    @api.model
    def send_pending_dian(self):
        data_lines_xml = ''
        data_credit_lines_xml = ''
        template_basic_data_xml = self._template_basic_data_xml()
        template_tax_data_xml = self._template_tax_data_xml()
        template_line_data_xml = self._template_line_data_xml()
        template_credit_line_data_xml = self._template_credit_line_data_xml()
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
            # prueba manual de xml
            #xlm_prueba_manual = self._prueba_manual_xml() 
            #xlm_prueba_resultado = self._verificacion_manual_xml()
            #digest_value = SubElement(reference, "DigestValue")
            #digest_value.text = digest
            #print 'ssssss: ', ssssssssss
            # Datos de encabezado de la factura            
            data_header_doc = self.env['account.invoice'].search([('id', '=', doc_send_dian.document_id.id)])
            # Constantes del documento
            data_constants_document = self._generate_data_constants_document(data_header_doc, dian_constants)            
            # Detalle de impuestos
            data_taxs = self._get_taxs_data(data_header_doc.id)
            data_taxs_xml = self._generate_taxs_data_xml(template_tax_data_xml, data_taxs)
            # Detalle líneas de factura
            if data_constants_document['InvoiceTypeCode'] == '1':
                data_lines_xml = self._generate_lines_data_xml(template_line_data_xml, data_header_doc.id)
            if data_constants_document['InvoiceTypeCode'] == '2':
                data_credit_lines_xml = self._generate_credit_lines_data_xml(template_credit_line_data_xml, data_header_doc.id)
            # Generar CUFE
            CUFE = self._generate_cufe(data_header_doc.id, data_constants_document['InvoiceID'], data_constants_document['IssueDateCufe'], 
                                    data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'],
                                    dian_constants['SupplierID'], data_constants_document['CustomerSchemeID'],
                                    data_constants_document['CustomerID'], data_constants_document['TechnicalKey'], data_constants_document['PayableAmount'], data_taxs)
            doc_send_dian.cufe = CUFE
            # Construye el documento XML sin firma
            data_xml_signature = ''
            data_xml_document = '<?xml version="1.0" encoding="UTF-8"?>' + self._generate_data_document_xml(template_basic_data_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature, data_credit_lines_xml)
            #data_xml_document = self._generate_data_document_xml(template_basic_data_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature, data_credit_lines_xml)

            #Genera la firma en el documento xml
            # print '\n\n\n'
            print 'data_xml_document sin firma: ', data_xml_document
            data_xml_signature = self._generate_signature(data_xml_document, template_signature_data_xml, dian_constants, data_constants_document)

            _logger.info("FIRMA")
            _logger.info( data_xml_signature )

            # Construye el documento XML con firma
            data_xml_document = '<?xml version="1.0" encoding="UTF-8"?>' + self._generate_data_document_xml(template_basic_data_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature, data_credit_lines_xml)
            print '\n\n\n'
            # print 'data_xml_signature: ', data_xml_signature
            print 'data_xml_document con firma: ', data_xml_document
            # Generar codigo DIAN
            doc_send_dian.dian_code = data_constants_document['InvoiceID']
            # Generar nombre del archvio xml
            doc_send_dian.xml_file_name = data_constants_document['FileNameXML']
            # Almacenar archivo xml
            doc_send_dian.xml_document = data_xml_document
            # Generar nombre archvio ZIP
            doc_send_dian.zip_file_name = data_constants_document['FileNameZIP']
            # Comprimir documento electrónico         
            Document = self._generate_zip_content(data_constants_document['FileNameXML'], data_constants_document['FileNameZIP'], data_xml_document, dian_constants['document_repository'])
            #Fecha y hora de la petición
            Created = self._generate_datetime_created()
            #doc_send_dian.date_document_dian = fields.Datetime.now()
            doc_send_dian.date_document_dian = data_constants_document['IssueDateSend']
            # Construye el XML de petición o envío  
            data_xml_send = self._generate_data_send_xml(template_send_data_xml, dian_constants,data_constants_document, Created, Document)
            # Enviar documento al DIAN (Petición).
            data_xml_send = '<?xml version="1.0" encoding="UTF-8"?>' + data_xml_send
            data_xml_send = data_xml_send.replace('\n','')
            headers = {'content-type': 'text/xml'} 
            try:
                response = requests.post(server_url['HABILITACION'],data=data_xml_send,headers=headers) 
            except:
                print("No existe comunicación con la DIAN")
                return
            # Almacena respuesta DIAN en archvio en disco
            xml_file_response = dian_constants['document_repository'] + '/' + 'response_' + data_constants_document['FileNameXML'] 
            f = open (xml_file_response,'w')
            f.write(response.content)
            f.close()
            # Obtiene solo la estructura xml y elimina archivo
            f = open (xml_file_response,'r')
            line_xml_response = f.readline()
            while line_xml_response != '':
                if line_xml_response.find("<SOAP-ENV:Envelope") == 0:
                    response_xml =  line_xml_response
                line_xml_response = f.readline()
            f.close()
            os.remove(xml_file_response)
            # Verifica respuesta
            response_xml_dict = xmltodict.parse(response_xml)
            if response_xml_dict['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns2:EnvioFacturaElectronicaRespuesta']['ns2:Response'] == '200':
                doc_send_dian.state = 'por_validar'
            else: 
                doc_send_dian.state = 'por_notificar'
            doc_send_dian.shipping_response = response_xml_dict['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns2:EnvioFacturaElectronicaRespuesta']['ns2:Response']
            #doc_send_dian.response_message_dian = u'Recepción de facturas: ' + response_xml_dict['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns2:EnvioFacturaElectronicaRespuesta']['ns2:Comments'] + '\n'
            doc_send_dian.response_message_dian = ' '
            # Generar código QR
            doc_send_dian.QR_code = self._generate_barcode(dian_constants, data_constants_document, CUFE, data_taxs)
        return 


    @api.model
    def _generate_signature(self, data_xml_document, template_signature_data_xml, dian_constants, data_constants_document):
        data_xml_keyinfo_base = ''
        data_xml_politics = ''
        data_xml_SignedProperties_base = ''
        data_xml_SigningTime = ''
        data_xml_SignatureValue = ''
        # Generar clave de referencia 0 para la firma del documento (referencia ref0)
        print '\n\n\n'
        print 'data_xml_document sin firma: ', data_xml_document  
        data_xml_signature_ref_zero = self._generate_signature_ref0(data_xml_document)
        # Generar certificado publico para la firma del documento en el elemento keyinfo 
        data_public_certificate_base = dian_constants['Certificate']
        # 1ra. Actualización de firma
        data_xml_signature = self._update_signature(template_signature_data_xml, data_xml_document, 
                                        data_xml_signature_ref_zero, data_public_certificate_base, 
                                        data_xml_keyinfo_base, data_xml_politics, 
                                        data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants, data_xml_SignatureValue)
        print '\n\n\n'
        print 'data_xml_signature 1 ref1: ', data_xml_signature
        # Generar clave de referencia 1 para la firma del documento (referencia keyinfo)
        data_xml_keyinfo_base = self._generate_signature_ref1(data_xml_signature)
        # Generar clave de politica de firma para la firma del documento (SigPolicyHash)
        data_xml_politics = self._generate_signature_politics(data_xml_signature, dian_constants['document_repository'])
        # Obtener la hora de Colombia desde la hora del pc
        data_xml_SigningTime = self._generate_signature_signingtime()
        # 2da. actualización de firma
        data_xml_signature = self._update_signature(template_signature_data_xml, data_xml_document, 
                                        data_xml_signature_ref_zero, data_public_certificate_base, 
                                        data_xml_keyinfo_base, data_xml_politics, 
                                        data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants, data_xml_SignatureValue)
        print '\n\n\n'
        print 'data_xml_signature 2 ref2: ', data_xml_signature
        # Generar clave de referencia 2 para la firma del documento (referencia SignedProperties)
        data_xml_SignedProperties_base = self._generate_signature_ref2(data_xml_signature)
        # Obtener la hora de Colombia desde la hora del pc
        #data_xml_SigningTime = self._generate_signature_signingtime()
        # 3ra. actualización de firma 
        data_xml_signature = self._update_signature(template_signature_data_xml, data_xml_document, 
                                        data_xml_signature_ref_zero, data_public_certificate_base, 
                                        data_xml_keyinfo_base, data_xml_politics, 
                                        data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants, data_xml_SignatureValue)
        print '\n\n\n'
        print 'data_xml_signature 3 SignatureValue: ', data_xml_signature
        # Aplicar la firma SignaturValue
        data_xml_SignatureValue = self._generate_SignatureValue(data_xml_signature, dian_constants['document_repository'])
        print '\n\n\n'
        print 'data_xml_SignatureValue: ', data_xml_SignatureValue
        # 4ta. actualización de firma 
        data_xml_signature = self._update_signature(template_signature_data_xml, data_xml_document, 
                                        data_xml_signature_ref_zero, data_public_certificate_base, 
                                        data_xml_keyinfo_base, data_xml_politics, 
                                        data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants, data_xml_SignatureValue)
        print '\n\n\n'
        print 'data_xml_signature 4 total: ', data_xml_signature
        #print 'ssss', ssss
        # Id URI Falta anilizar si es con id distintos por xml
        #template_signature_data_xml_id = self._template_signature_data_xml_id()
        #data_xml_signature_id = self._update_signature_id(template_signature_data_xml_id, data_xml_document, 
        #                                data_xml_signature_ref_zero, data_public_certificate_base, 
        #                                data_xml_keyinfo_base, data_xml_politics, 
        #                                data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants,
        #                                data_constants_document, data_xml_SignatureValue)
        return data_xml_signature


    @api.model
    def _get_dian_constants(self):
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        company = self.env['res.company'].search([('id', '=', user.company_id.id)])
        partner = company.partner_id 
        dian_constants = {}
        dian_constants['document_repository'] = company.document_repository                   # Ruta en donde se almacenaran los archivos que utiliza y genera la Facturación Electrónica
        dian_constants['Username'] = company.software_identification_code       # Identificador del software en estado en pruebas o activo 
        dian_constants['Password'] = hashlib.new('sha256',company.software_pin).hexdigest()       # Es el resultado de aplicar la función de resumen SHA-256 sobre la contraseña del software en estado en pruebas o activo
        dian_constants['IdentificationCode'] = partner.country_id.code          # Identificador de pais
        #dian_constants['ProviderID'] = partner.formatedNit.replace('.','').replace('-','') if partner.formatedNit else '' # ID Proveedor de software o cliente si es software propio
        dian_constants['ProviderID'] = partner.xidentification     if partner.xidentification else '' # ID Proveedor de software o cliente si es software propio
        dian_constants['SoftwareID'] = company.software_identification_code     # ID del software a utilizar
        #dian_constants['SoftwareID'] = '8Odoo77'
        #dian_constants['SoftwareSecurityCode'] = self._generate_software_security_code(company.software_identification_code, company.software_pin) # Código de seguridad del software: (hashlib.new('sha384', str(self.company_id.software_id) + str(self.company_id.software_pin)))
        dian_constants['SoftwareSecurityCode'] = self._generate_software_security_code(company.software_identification_code, '8Odoo77') # Código de seguridad del software: (hashlib.new('sha384', str(self.company_id.software_id) + str(self.company_id.software_pin)))
        dian_constants['SeedCode'] = company.seed_code
        dian_constants['UBLVersionID'] = 'UBL 2.0'                              # Versión base de UBL usada. Debe marcar UBL 2.0
        dian_constants['ProfileID'] = 'DIAN 1.0'                                # Versión del Formato: Indicar versión del documento. Debe usarse "DIAN 1.0"
        dian_constants['SupplierAdditionalAccountID'] = '2' if partner.company_type == 'company' else '1' # Persona natural o jurídica (persona natural, jurídica, gran contribuyente, otros)
        #dian_constants['SupplierID'] = partner.formatedNit.replace('.','').replace('-','') if partner.formatedNit else '' # Identificador fiscal: En Colombia, el NIT
        dian_constants['SupplierID'] = partner.xidentification     if partner.xidentification else '' # Identificador fiscal: En Colombia, el NIT
        dian_constants['SupplierSchemeID'] = partner.doctype
        dian_constants['SupplierPartyName'] = partner.name                      # Nombre Comercial
        dian_constants['SupplierDepartment'] = partner.state_id.name            # Estado o departamento (No requerido)
        dian_constants['SupplierCitySubdivisionName'] = partner.xcity.name      # Cuidad, municipio o distrito (No requerido)
        dian_constants['SupplierCityName'] = partner.city                       # Municipio o ciudad
        dian_constants['SupplierLine'] = partner.street                         # Calle
        dian_constants['SupplierCountry'] = partner.country_id.code 
        dian_constants['SupplierTaxLevelCode'] = partner.x_pn_retri             # Régimen al que pertenece Debe referenciar a una lista de códigos con los por ejemplo: • Común • Simplificado • No aplica valores correspondientes
        dian_constants['SupplierRegistrationName'] = company.trade_name         # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        
        #archvivo_pem = '/tmp/Certificado/744524.pem' 
        #pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archvivo_pem, 'rb').read())
        #dian_constants['Certificate'] = base64.b64encode(company.digital_certificate.replace('\n',''))
        dian_constants['Certificate'] = base64.b64encode(company.digital_certificate)

                     # KeyInfo: a partir del certificado público convirtiendolo a base64
        #dian_constants['Certificate'] = company.digital_certificate
        dian_constants['NitSinDV'] = partner.xidentification                    # Nit sin digito validador
        dian_constants['CertDigestDigestValue'] = self._generate_CertDigestDigestValue(company.digital_certificate) #Falta se presume que es el certificado publico convertido a sha256 base64
        #dian_constants['CertDigestDigestValue'] = company.digital_certificate #Falta se presume que es el certificado publico convertido a sha256 base64
        dian_constants['IssuerName'] = company.issuer_name                      # Nombre del proveedor del certificado
        dian_constants['SerialNumber'] = company.serial_number                  # Serial del certificado
        # serial completo sin los dos punto
        #dian_constants['IssuerName'] = '7407950780564486000'
        # serial por segmeto de dos puntos
        #dian_constants['IssuerName'] = '1022068325210131185106'
        return dian_constants


    def _template_basic_data_xml(self):
        template_basic_data_xml = """<fe:%(TypeDocument)s xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:clm54217="urn:un:unece:uncefact:codelist:specification:54217:2001" xmlns:clm66411="urn:un:unece:uncefact:codelist:specification:66411:2001" xmlns:clmIANAMIMEMediaType="urn:un:unece:uncefact:codelist:specification:IANAMIMEMediaType:2003" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:qdt="urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:udt="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xsi:schemaLocation="http://www.dian.gov.co/contratos/facturaelectronica/v1 http://www.dian.gov.co/micrositios/fac_electronica/documentos/XSD/r0/DIAN_UBL.xsd urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2 http://www.dian.gov.co/micrositios/fac_electronica/documentos/common/UnqualifiedDataTypeSchemaModule-2.0.xsd urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2 http://www.dian.gov.co/micrositios/fac_electronica/documentos/common/UBL-QualifiedDatatypes-2.0.xsd">
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
<ext:ExtensionContent>%(data_xml_signature)s</ext:ExtensionContent>
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
<cac:Contact>
<cbc:Telephone/>
<cbc:ElectronicMail>%(CustomerEmail)s</cbc:ElectronicMail>
</cac:Contact>
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
</fe:LegalMonetaryTotal>%(data_lines_xml)s%(data_credit_lines_xml)s
</fe:%(TypeDocument)s>""" 
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


    def _template_credit_line_data_xml(self):
        template_credit_line_data_xml = """
<cac:CreditNoteLine>
<cbc:ID>%(CRLinea)s</cbc:ID>
<cbc:LineExtensionAmount currencyID="COP">%(CRLineExtensionAmount)s</cbc:LineExtensionAmount>
<cac:Item>
<cbc:Description>%(CRDescription)s</cbc:Description>
</cac:Item>
</cac:CreditNoteLine>""" 
        return template_credit_line_data_xml


    def _template_signature_data_xml(self):
        #<ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
        #<ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
        template_signature_data_xml = """<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5">
<ds:SignedInfo>
<ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
<ds:Reference Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-ref0" URI="">
<ds:Transforms>
<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
</ds:Transforms>
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>%(data_xml_signature_ref_zero)s</ds:DigestValue>
</ds:Reference>
<ds:Reference URI="#xmldsig-87d128b5-aa31-4f0b-8e45-3d9cfa0eec26-keyinfo">
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>%(data_xml_keyinfo_base)s</ds:DigestValue>
</ds:Reference>
<ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-signedprops">
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>%(data_xml_SignedProperties_base)s</ds:DigestValue>
</ds:Reference>
</ds:SignedInfo>
<ds:SignatureValue Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-sigvalue">%(SignatureValue)s</ds:SignatureValue>
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
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>%(CertDigestDigestValue)s</ds:DigestValue>
</xades:CertDigest>
<xades:IssuerSerial>
<ds:X509IssuerName>%(IssuerName)s</ds:X509IssuerName>
<ds:X509SerialNumber>%(SerialNumber)s</ds:X509SerialNumber>
</xades:IssuerSerial>
</xades:Cert>
</xades:SigningCertificate>
<xades:SignaturePolicyIdentifier>
<xades:SignaturePolicyId>
<xades:SigPolicyId>
<xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
</xades:SigPolicyId>
<xades:SigPolicyHash>
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
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

#<wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">

    def _template_send_data_xml(self):
        template_send_data_xml = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:rep="http://www.dian.gov.co/servicios/facturaelectronica/ReportarFactura">
<soapenv:Header>
<wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
<wsse:UsernameToken>
<wsse:Username>%(Username)s</wsse:Username>
<wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">%(Password)s</wsse:Password>
<wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">%(Nonce)s</wsse:Nonce>
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


    def _generate_data_constants_document(self, data_header_doc, dian_constants):
        NitSinDV = dian_constants['NitSinDV']
        data_constants_document = {}
        data_resolution  = self._get_resolution_dian()
        # Generar nombre del archvio xml
        data_constants_document['FileNameXML'] = self._generate_xml_filename(data_resolution, NitSinDV, data_header_doc.type)
        # Generar Id de Signature
        # FileNameXML = hashlib.new('sha256', data_constants_document['FileNameXML'])
        # FileNameXML = FileNameXML.digest()
        # FileNameXML = base64.b64encode(FileNameXML)
        # print ''
        # print 'FileNameXML', data_constants_document['FileNameXML']
        # print 'FileNameXML base64', FileNameXML
        # print ''

        data_constants_document['FileNameZIP'] = self._generate_zip_filename(data_resolution, NitSinDV, data_header_doc.type)
        data_constants_document['InvoiceAuthorization'] = data_resolution['InvoiceAuthorization']  # Número de resolución
        data_constants_document['StartDate'] = data_resolution['StartDate']                        # Fecha desde resolución
        data_constants_document['EndDate'] = data_resolution['EndDate']                            # Fecha hasta resolución
        data_constants_document['Prefix'] = data_resolution['Prefix']                              # Prefijo de número de factura
        data_constants_document['From'] = data_resolution['From']                                  # Desde la secuencia
        data_constants_document['To'] = data_resolution['To']                                      # Hasta la secuencia
        data_constants_document['InvoiceID'] = data_resolution['InvoiceID']                        # Número de documento dian
        data_constants_document['Nonce'] = self._generate_nonce(data_resolution['InvoiceID'], dian_constants['SeedCode']) # semilla para generar números aleatorios
        data_constants_document['TechnicalKey'] = data_resolution['TechnicalKey']                  # Clave técnica de la resolución de rango
        data_constants_document['LineExtensionAmount'] = self._complements_second_decimal(data_header_doc.amount_untaxed)         # Total Importe bruto antes de impuestos: Total importe bruto, suma de los importes brutos de las líneas de la factura.
        data_constants_document['TaxExclusiveAmount'] = self._complements_second_decimal(data_header_doc.amount_untaxed)          # Total Base Imponible (Importe Bruto+Cargos-Descuentos): Base imponible para el cálculo de los impuestos
        data_constants_document['PayableAmount'] = self._complements_second_decimal(data_header_doc.amount_total)                 # Total de Factura: Total importe bruto + Total Impuestos-Total Impuesto Retenidos
        #data_constants_document['IssueDate'] = data_header_doc.date_invoice                     # Fecha de emisión de la factura a efectos fiscales        
        date_invoice_cufe = self._generate_datetime_IssueDate()
        data_constants_document['IssueDate'] = date_invoice_cufe['IssueDate'] 
        data_constants_document['IssueDateSend'] = date_invoice_cufe['IssueDateSend']
        data_constants_document['IssueDateCufe'] = date_invoice_cufe['IssueDateCufe']
        data_constants_document['IssueTime'] = self._get_time()                                 # Hora de emisión de la fcatura
        data_constants_document['InvoiceTypeCode'] = self._get_doctype(data_header_doc.type)    # Tipo de Factura, código: facturas de venta, y transcripciones; tipo = 1 para factura de venta
        data_constants_document['DocumentCurrencyCode'] = data_header_doc.currency_id.name      # Divisa de la Factura
        data_constants_document['CustomerAdditionalAccountID'] = '2' if data_header_doc.partner_id.company_type == 'company' else '1'
        #data_constants_document['CustomerID'] = data_header_doc.partner_id.formatedNit.replace('.','').replace('-','') if data_header_doc.partner_id.formatedNit else ''# Identificador fiscal: En Colombia, el NIT
        data_constants_document['CustomerID'] = data_header_doc.partner_id.xidentification if data_header_doc.partner_id.xidentification else ''# Identificador fiscal: En Colombia, el NIT
        data_constants_document['CustomerSchemeID'] = data_header_doc.partner_id.doctype                # tipo de identificdor fiscal 
        data_constants_document['CustomerPartyName'] = data_header_doc.partner_id.name          # Nombre Comercial
    #--0CustomerDepartment = 'PJ - 800199436 - Adquiriente FE'
        data_constants_document['CustomerDepartment'] = data_header_doc.partner_id.state_id.name
    #--0CustomerCitySubdivisionName = 'PJ - 800199436 - Adquiriente FE'
        data_constants_document['CustomerCitySubdivisionName'] = data_header_doc.partner_id.xcity.name
        data_constants_document['CustomerCityName'] = data_header_doc.partner_id.city
        data_constants_document['CustomerCountry'] = data_header_doc.partner_id.country_id.code
        data_constants_document['CustomerAddressLine'] = data_header_doc.partner_id.street
    #--1TaxLevelCode = '0'  # Régimen al que pertenece Debe referenciar a una lista de códigos con los por ejemplo: • Común • Simplificado • No aplica valores correspondientes
        data_constants_document['TaxLevelCode'] = data_header_doc.partner_id.x_pn_retri
    #--1RegistrationName = 'PJ - 800199436' # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        data_constants_document['RegistrationName'] = data_header_doc.partner_id.companyName
        data_constants_document['CustomerEmail'] = data_header_doc.partner_id.email if data_header_doc.partner_id.email else ''
        if data_constants_document['InvoiceTypeCode'] == '1':
            data_constants_document['TypeDocument'] = 'Invoice'
        if data_constants_document['InvoiceTypeCode'] == '2':
            data_constants_document['TypeDocument'] = 'CreditNote' 
    # Id URI Falta anilizar si es con id distintos por xml
        # # IdXml = hashlib.sha1(data_constants_document['InvoiceID'])
        # # IdXml = IdXml.hexdigest()
        # # print '\n\n\n'
        # # print 'IdXml1: ', IdXml
        # IdXml = base64.b64encode(data_constants_document['InvoiceID'])

        # #IdXml = IdXml.hexdigest()
        # print '\n\n\n'
        # print 'IdXml2: ', IdXml
        # print ssss

        # prueba = 'MIIILDCCBhSgAwIBAgIIfq9P6xyRMBEwDQYJKoZIhvcNAQELBQAwgbQxIzAhBgkqhkiG9w0BCQEWFGluZm9AYW5kZXNzY2QuY29tLmNvMSMwIQYDVQQDExpDQSBBTkRFUyBTQ0QgUy5BLiBDbGFzZSBJSTEwMC4GA1UECxMnRGl2aXNpb24gZGUgY2VydGlmaWNhY2lvbiBlbnRpZGFkIGZpbmFsMRMwEQYD'
        # prueba = hashlib.new('sha1', prueba)
        # prueba = prueba.digest()
        # prueba = base64.b64encode(prueba)
        # print '\n\n\n'
        # print 'prueba: ', prueba
        # print ssss

        # CP = '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'
        # CP = hashlib.new('sha256', CP)
        # CP = CP.digest()
        # print '\n\n\n'
        # print 'CP digest: ',  CP 
        # CP = base64.b64encode(CP)
        # print '\n\n\n'
        # print 'CP digest base64: ', CP
        # print '\n\n\n'
        # print ssss

        # CP1 = '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'
        # CP1 = hashlib.new('sha1', CP1)
        # CP1 = CP1.hexdigest()
        # print '\n\n\n'
        # print 'CP1 digest: ',  CP1 
        # CP1 = base64.b64encode(CP1)
        # print '\n\n\n'
        # print 'CP1 digest base64: ', CP1


        IdXml = 'sdsad-543543-dsdas-43423-4567'
        data_constants_document['IdSignature'] = IdXml
        data_constants_document['IdReference_zero'] = IdXml
        data_constants_document['URIReference_keyinfo'] = IdXml
        data_constants_document['URIReference_signedprops'] = IdXml
        data_constants_document['IdSignatureValue'] = IdXml
        data_constants_document['IdKeyInfo'] = IdXml
        data_constants_document['IdSignedProperties'] = IdXml
        data_constants_document['Target'] = IdXml
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
            iva_01 += item_tax.amount if item_tax.tax_id.tax_group_id.id  == 5 else 0.0 
            # Falta
            ica_03 += item_tax.amount if item_tax.tax_id.tax_group_id.id  == 4 else 0.0 
            ico_02 += item_tax.amount if item_tax.tax_id.tax_group_id.id  not in (5,4) else 0.0  
            tax_percentage_iva_01 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if item_tax.tax_id.tax_group_id.id  == 5 else tax_percentage_iva_01
            # Falta
            tax_percentage_ica_03 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if item_tax.tax_id.tax_group_id.id  == 4 else tax_percentage_ico_02
            tax_percentage_ico_02 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if item_tax.tax_id.tax_group_id.id  not in (5,4) else tax_percentage_ica_03
            invoice_lines = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id), ('invoice_line_tax_ids', 'in', item_tax.tax_id.id)])
            for invoice_line in invoice_lines:
                total_base_iva_01 += invoice_line.price_subtotal if item_tax.tax_id.tax_group_id.id  == 5 else 0
                # Falta
                total_base_ica_03 += invoice_line.price_subtotal if item_tax.tax_id.tax_group_id.id  == 4 else 0
                total_base_ico_02 += invoice_line.price_subtotal if item_tax.tax_id.tax_group_id.id  not in (5,4) else 0
        
        dic_taxs_data['iva_01'] = self._complements_second_decimal(iva_01)
        dic_taxs_data['tax_percentage_iva_01'] = self._complements_second_decimal(tax_percentage_iva_01)
        dic_taxs_data['total_base_iva_01'] = self._complements_second_decimal(total_base_iva_01)
        dic_taxs_data['ica_03'] = self._complements_second_decimal(ica_03)
        dic_taxs_data['tax_percentage_ica_03'] = self._complements_second_decimal(tax_percentage_ica_03)
        dic_taxs_data['total_base_ica_03'] = self._complements_second_decimal(total_base_ica_03)
        dic_taxs_data['ico_02'] = self._complements_second_decimal(ico_02)
        dic_taxs_data['tax_percentage_ico_02'] = self._complements_second_decimal(tax_percentage_ico_02)
        dic_taxs_data['total_base_ico_02'] = self._complements_second_decimal(total_base_ico_02)
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
        if data_taxs['ico_02'] != '0.00':
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
        if data_taxs['ica_03'] != '0.00':
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


    def _generate_lines_data_xml(self, template_line_data_xml, invoice_id):
        ILLinea = 0
        data_line_xml = ''
        data_lines_doc = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)])
        for data_line in data_lines_doc:
            ILLinea += 1
            ILInvoicedQuantity = self._complements_second_decimal(data_line.quantity)          # 13.1.1.9 - Cantidad: Cantidad del artículo solicitado. Número de unidades servidas/prestadas.
            ILLineExtensionAmount = self._complements_second_decimal(data_line.price_subtotal) # 13.1.1.12 - Costo Total: Coste Total. Resultado: Unidad de Medida x Precio Unidad.
            ILChargeIndicator = 'true'                       # Indica que el elemento es un Cargo (5.1.1) y no un descuento (4.1.1)
            ILAmount =  self._complements_second_decimal(data_line.discount)                   # Valor Descuento: Importe total a descontar.
            ILDescription = data_line.name
            ILPriceAmount = self._complements_second_decimal(data_line.price_unit)             # Precio Unitario   
            data_line_xml += template_line_data_xml % {'ILLinea' : ILLinea,
                                                    'ILInvoicedQuantity' : ILInvoicedQuantity,
                                                    'ILLineExtensionAmount' : ILLineExtensionAmount,
                                                    'ILAmount' : ILAmount,
                                                    'ILDescription' : ILDescription,
                                                    'ILPriceAmount' : ILPriceAmount,
                                                    'ILChargeIndicator' : ILChargeIndicator,
                                                    }
        return data_line_xml


    def _generate_credit_lines_data_xml(self , template_credit_line_data_xml, invoice_id):
        CRLinea = 0
        data_credit_note_line_xml = ''
        data_lines_doc = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)])
        for data_line in data_lines_doc:
            CRLinea += 1
            CRLineExtensionAmount = self._complements_second_decimal(data_line.price_subtotal) # 13.1.1.12 - Costo Total: Coste Total. Resultado: Unidad de Medida x Precio Unidad.
            CRDescription = data_line.name
            data_credit_note_line_xml += template_credit_line_data_xml % {'CRLinea' : CRLinea,
                                                        'CRLineExtensionAmount' : CRLineExtensionAmount,
                                                        'CRDescription' : CRDescription,
                                                        }
        return data_credit_note_line_xml


    @api.model
    def _generate_cufe(self, invoice_id, NumFac, FecFac, Time, ValFac, NitOFE, TipAdq, NumAdq, ClTec, ValPag, data_taxs):
        #FecFac = FecFac.replace('-','')+Time.replace(':','')
        ValFac = str(ValFac)
        # Obtine los distintos impuestos
        #data_tax_detail_doc = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice_id)])
        CodImp1 = '01' 
        ValImp1 = str(data_taxs['iva_01'])
        CodImp2 = '02'
        ValImp2 = str(data_taxs['ico_02'])
        CodImp3 = '03'
        ValImp3 = str(data_taxs['ica_03'])
        ValPag  = str(ValPag)
        TipAdq  = str(TipAdq)
        # print '\n\n\n'
        # print 'NumFac', NumFac     
        # print 'FecFac', FecFac
        # print 'ValFac', ValFac
        # print 'CodImp1', CodImp1
        # print 'ValImp1', ValImp1
        # print 'CodImp2', CodImp2
        # print 'ValImp2', ValImp2
        # print 'CodImp3', CodImp3
        # print 'ValImp3', ValImp3
        # print 'ValPag', ValPag
        # print 'NitOFE', NitOFE
        # print 'TipAdq', TipAdq
        # print 'NumAdq', NumAdq
        # print 'ClTec', ClTec
        # print '\n\n\n'
        #CUFE = hashlib.sha1(NumFac +';'+ FecFac +';'+ ValFac +';'+ CodImp1 +';'+ ValImp1 +';'+ CodImp2 +';'+ ValImp2 +';'+ CodImp3 +';'+ ValImp3 +';'+ ValPag +';'+ NitOFE +';'+ TipAdq +';'+ NumAdq +';'+ ClTec)
        CUFE = hashlib.sha1(NumFac+FecFac+ValFac+CodImp1+ValImp1+CodImp2+ValImp2+CodImp3+ValImp3+ValPag+NitOFE+TipAdq+NumAdq+ClTec)
        CUFE = CUFE.hexdigest()
        return CUFE


    def _generate_data_document_xml(self, template_basic_data_xml, dc, dcd, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature, data_credit_lines_xml):
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
                        'CustomerEmail' : dcd['CustomerEmail'],
                        'CustomerAddressLine' : dcd['CustomerAddressLine'],                                
                        'TaxLevelCode' : dcd['TaxLevelCode'],
                        'RegistrationName' : dcd['RegistrationName'],
                        'TotalLineExtensionAmount' : dcd['LineExtensionAmount'],
                        'TotalTaxExclusiveAmount' : dcd['TaxExclusiveAmount'],
                        'TypeDocument' : dcd['TypeDocument'],
                        'data_taxs_xml' : data_taxs_xml,
                        'data_lines_xml' : data_lines_xml,
                        'data_xml_signature' : data_xml_signature,
                        'data_credit_lines_xml' : data_credit_lines_xml,
                        }

        template_basic_data_xml = template_basic_data_xml.replace('\n','')
        template_basic_data_xml = etree.tostring(etree.fromstring(template_basic_data_xml), method="c14n")
        return template_basic_data_xml


    @api.model
    def _generate_data_send_xml(self, template_send_data_xml, dian_constants, data_constants_document, 
                                Created, Document):
        data_send_xml = template_send_data_xml % {'Username' : dian_constants['Username'],
                        'Password' : dian_constants['Password'],
                        'Nonce' : data_constants_document['Nonce'],
                        'Created' : Created,
                        'NIT' : dian_constants['SupplierID'],
                        'InvoiceNumber' : data_constants_document['InvoiceID'],
                        'IssueDate' : data_constants_document['IssueDateSend'],
                        'Document' : Document,
                        }
        return data_send_xml


    @api.model
    def _generate_signature_ref0(self, data_xml_document):
        # 1er paso generar la referencia 0 que consiste en obtener keyvalue desde todo el xml del documento
        #          electronico aplicando el algoritmo SHA256 y convirtiendolo a base64
        #1data_xml_document = data_xml_document.replace('\n','')
        #1data_xml_c14n = etree.tostring(etree.fromstring(data_xml_document), method="c14n")
        data_xml_sha256 = hashlib.new('sha256', data_xml_document)
        data_xml_digest = data_xml_sha256.digest()
        # Digest value del documento
        data_xml_signature_ref0 = base64.b64encode(data_xml_digest)

        # print '\n\n\n'
        # print 'data_xml_document ref0: ', data_xml_document
        # print '\n'
        # print 'sssss', sssss
        # print 'data_xml_sha256 ref0: ', data_xml_sha256
        # print '\n'
        # print 'data_xml_digest ref0: ', data_xml_digest
        # print '\n'
        # print 'data_xml_signature_ref0: ', data_xml_signature_ref0
        # print '\n'
        #print 'ssss: ', ssss

        return data_xml_signature_ref0


    @api.model
    def _update_signature(self, template_signature_data_xml, data_xml_document, 
                                data_xml_signature_ref_zero, data_public_certificate_base, 
                                data_xml_keyinfo_base, data_xml_politics, 
                                data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants,
                                data_xml_SignatureValue):
        data_xml_signature = template_signature_data_xml % {'data_xml_signature_ref_zero' : data_xml_signature_ref_zero,                                        
                                        'data_public_certificate_base' : data_public_certificate_base,
                                        'data_xml_keyinfo_base' : data_xml_keyinfo_base,
                                        'data_xml_politics' : data_xml_politics,
                                        'data_xml_SignedProperties_base' : data_xml_SignedProperties_base,
                                        'data_xml_SigningTime' : data_xml_SigningTime, 
                                        'CertDigestDigestValue' : dian_constants['CertDigestDigestValue'],
                                        'IssuerName' : dian_constants['IssuerName'], 
                                        'SerialNumber' : dian_constants['SerialNumber'],
                                        'SignatureValue' : data_xml_SignatureValue,                                      
                                        }
        
        data_xml_signature = data_xml_signature.replace('\n','')
        data_xml_signature = etree.tostring(etree.fromstring(data_xml_signature), method="c14n")
        #print 'data_xml_signature enter: ', data_xml_signature
        return data_xml_signature


    @api.multi
    def _generate_signature_ref1(self, data_xml_signature):
        # Generar la referencia 1 que consiste en obtener keyvalue desde el keyinfo contenido 
        # en el documento electrónico aplicando el algoritmo SHA256 y convirtiendolo a base64
        data_xml_keyinfo = etree.fromstring(data_xml_signature)
        element_xml_keyinfo = etree.tostring(data_xml_keyinfo[2])
        # element_xml_keyinfo = element_xml_keyinfo.replace('\n','')
        # data_xml_keyinfo_c14n = etree.tostring(etree.fromstring(element_xml_keyinfo), method="c14n")
        # print '\n\n\n'
        # print 'element_xml_keyinfo ref1: ', element_xml_keyinfo
        data_xml_keyinfo_sha256 = hashlib.new('sha256', element_xml_keyinfo)
        data_xml_keyinfo_digest = data_xml_keyinfo_sha256.digest()
        data_xml_keyinfo_base = base64.b64encode(data_xml_keyinfo_digest)

        # print '\n\n\n'
        # # print 'data_xml_keyinfo_c14n: ', data_xml_keyinfo_c14n
        # # print '\n'
        # print 'data_xml_keyinfo_sha256  ref1: ', data_xml_keyinfo_sha256
        # print '\n'
        # print 'data_xml_keyinfo_digest  ref1: ', data_xml_keyinfo_digest
        # print '\n'
        # print 'data_xml_keyinfo_base ref1: ', data_xml_keyinfo_base
        # print '\n'
        # print 'ssss: ', ssss

        return data_xml_keyinfo_base


    @api.multi
    def _generate_signature_politics(self, data_xml_signature, document_repository):
        # Paso generar la referencia 2 que consiste en obtener keyvalue desde el documento de 
        # politica aplicando el algoritmo SHA1 antes del 20 de septimebre de 2016 y sha256 
        # despues de esa fechay convirtiendolo a base64. Se  puede  utilizar  
        # como una constante ya que no variará en años segun lo indica la DIAN.
        #  
        # 
        politicav2 = document_repository+'/politicadefirmav2.pdf'
        politicav2 = open(politicav2,'r')
        contenido_politicav2 = politicav2.read()
        # politicav2_sha1 = hashlib.new('sha1', contenido_politicav2)
        # politicav2_digest = politicav2_sha1.digest()
        # politicav2_base = base64.b64encode(politicav2_digest)

        # Cambiado el algoritmo de encriptación para los certificados digitales emitidos despues 
        # del 30 de septiembre de 2016 per anexo tecnico 2 pagina 29        
        # politicav2_sha256 = hashlib.new('sha256', contenido_politicav2)
        # politicav2_digest = politicav2_sha256.digest()
        # politicav2_base = base64.b64encode(politicav2_digest)
        # data_xml_politics = politicav2_base
        data_xml_politics = 'dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y='
        #data_xml_politics = 'sbcECQ7v+y/m3OcBCJyvmkBhtFs='
        return data_xml_politics


    @api.multi
    def _generate_signature_ref2(self, template_signature_data_xml):
        # Generar la referencia 2, se obtine desde el elemento SignedProperties que se 
        # encuentra en la firma aplicando el algoritmo SHA256 y convirtiendolo a base64.
        data_xml_SignedProperties = etree.fromstring(template_signature_data_xml)
        data_xml_SignedProperties = etree.tostring(data_xml_SignedProperties[3])
        data_xml_SignedProperties = etree.fromstring(data_xml_SignedProperties)
        data_xml_SignedProperties = etree.tostring(data_xml_SignedProperties[0])
        data_xml_SignedProperties = etree.fromstring(data_xml_SignedProperties)
        data_xml_SignedProperties = etree.tostring(data_xml_SignedProperties[0])
        #1data_xml_SignedProperties = data_xml_SignedProperties.replace('\n','')
        #1data_xml_SignedProperties_c14n = etree.tostring(etree.fromstring(data_xml_SignedProperties), method="c14n")
        data_xml_SignedProperties_sha256 = hashlib.new('sha256', data_xml_SignedProperties)
        data_xml_SignedProperties_digest = data_xml_SignedProperties_sha256.digest()
        data_xml_SignedProperties_base = base64.b64encode(data_xml_SignedProperties_digest)
        
        # print '\n\n\n'
        # print 'data_xml_SignedProperties  ref2: ',  data_xml_SignedProperties
        # print '\n'
        # print 'data_xml_SignedProperties_sha256 ref2: ', data_xml_SignedProperties_sha256
        # print '\n'
        # print 'data_xml_SignedProperties_digest ref2: ', data_xml_SignedProperties_digest
        # print '\n'
        # print 'data_xml_SignedProperties_base ref2: ', data_xml_SignedProperties_base
        # print '\n'
        # print 'ssss: ', ssss


        return data_xml_SignedProperties_base


    @api.multi
    def _generate_CertDigestDigestValue(self, digital_certificate):
        CertDigestDigestValue256 = hashlib.new('sha256', digital_certificate)
        CertDigestDigestValue256_digest = CertDigestDigestValue256.digest()
        CertDigestDigestValue = base64.b64encode(CertDigestDigestValue256_digest)
        return CertDigestDigestValue


    @api.multi
    def _generate_SignatureValue(self, data_xml_signature, document_repository):
        data_xml_signature = etree.fromstring(data_xml_signature)
        data_xml_signature = etree.tostring(data_xml_signature[0])
        #data_xml_signature = data_xml_signature.replace('\n','')
        #data_xml_SignatureValue_c14n = etree.tostring(etree.fromstring(data_xml_signature), method="c14n")
        archivo_key = document_repository+'/plastinorte.com.key'
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(archivo_key, 'rb').read())
        signature = crypto.sign(key, data_xml_signature, 'sha256')
        SignatureValue = base64.b64encode(signature)

        archivo_pem = document_repository+'/744524.pem'
        pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        validacion = crypto.verify(pem, signature, data_xml_signature, 'sha256')


        print '\n\n\n'
        print 'data_xml_signature SignatureValue: ', data_xml_signature
        print '\n'
        print 'key SignatureValue: ', key
        print '\n'
        print 'signature SignatureValue: ', signature
        print '\n'
        print 'SignatureValue SignatureValue: ', SignatureValue
        print '\n'
        print 'validacion: ', validacion


        # print 'SSSSS: ', SSSS


        #if key.startswith('-----BEGIN '):
        #pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key)
        #else:
        #    pkey = crypto.load_pkcs12(key, password).get_privatekey()
        # print 'key', key
        # data = "data"
        # sign = OpenSSL.crypto.sign(key, data_xml_SignatureValue_c14n, "sha256") 
        # print sign


        #print 'ssss: ', sssss

        # key = crypto.load_privatekey(type_,privkey.encode('ascii'))
        # signature = crypto.sign(key,signed_info_c14n,'sha1')
        # signature_value.text = textwrap.fill(base64.b64encode(signature).decode(),64)

        #signature = signature.digest()
        


        # archvivo_cer = '/tmp/Certificado/plastinorte.com.csr' 
        # archvivo_pem = '/tmp/Certificado/744524.pem' 
         
        #cer = crypto.load_certificate(crypto.FILETYPE_PEM, open(archvivo_cer, 'rb').read())
        # pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archvivo_pem, 'rb').read())
        
        #key = crypto.load_certificate(crypto.FILETYPE_PEM, open(archvivo_key, 'rb').read())
        # print '\n\n\n'
        # print 'key: ', key
        # print '\n\n\n'
        # print 'pem: ', pem
        # print '\n\n\n'
        # print 'key: ', key

        #key = 'MIIEogIBAAKCAQEAmEuFMRb71oBkU79YTfyrgkAydKvXvPUIWUzShghOZ0KYQDK5MUEvzUZFMzDVpi5Uc5jh0Z4yB95cqGEfugjA5KxmLByh7jU3Q55bg7nvVExlTT/CqRzLDMD31Sw4PDHCePqV4XIKZMgwvHEoje5dgm6xyvI8KOQtMVp/vfB53P+7LoDW0s2Vvh0YE/TBQTyn0e3fJ43OzSnR67koMpQmgri0ndNIzTslRVP3QEMKBDOFWwXin6HsrAjrNcDqOVSp2e3hVYPymlDBfY2vD56jKViL2MV2A7YH6cFVQJbfmqVgPLgtBU0kxpgxZ5h96T5VfFT0e/Q1uIRjnhy2lWzIxQIDAQABAoIBAD0h23YoFrE02pDvdv/fE+113YsNy8zSwyYtezhIL0it57WlZsdJtml88pwo1yoc4NOCI+tjyAt2i9UfH4AqsVtZhK3iVHHtNKDU+UE4KsS44dUPahE+OJeHAjS0ymIHS1wKoo1bnKZ14XJTLgdDDpAj5QRlFhcH+Mgd3rccx54Y/sB62L4TqreYMYQ2P2WTZ/mY7LfSDW5glBv12Ef3kwhz0yLXeXzDBlOz45UPYYL9FM2F8fL819ZEXLsPxUvq3AZmGS9Cpq1L0KjtDEdkyYkB6JzDnWkrjOtYBcNQJTEZ7gjI50hj7aYgV60U/R9qceYRUiPdIqZFhav/m/swICUCgYEAxyh9e7ZTuVrCSerTFkYGFi/0CqM2+FHuhAdggoUsoxMx+DLcmUraG2Qs/I79PyCUr4hVr8HZfVbw1VMpBbXnmbokahUbafrQaRJFNYphq9+aPPsabOge3kVeNsf96d/n82BhKlLN/t6TY4wB3YccOhFpQZGeueYFzcbYeVz85dsCgYEAw8L3/NXrpAMuf3NLsPU/9ETFXavymACoH8U06+Fj3TxA9QwWdHUwL9WC90v4fdzZ+V2JROOnJV+y/030DcbkKhCu0ORzGjj31flkMnBpohLQ3ogR36yYoZcutJn+/LRQ7iInCOmkQMEahDeevYjCwdshLgiJe4RA6MF8O6LgXd8CgYBptcI1QifagKQT3ALDFdPxPu7IHq30zHhPuCKv5MQ2ot+pIEYbT7HJTDjcrYEaWs7RBQqGSdyJPPaEJKnnkBAodrcRX7a3YBvzSXFW4+bH9d3GdHooSGTqEePaK/lIhEJ32jZ44o7Ys4eEFTKARVDkOY2m8gZQIhn+iYcplAPgdQKBgDWrCu+e+hYh5Sp9wl+GLP1bqTwv+rcfXvguyX5tcUJi1XAY20McKZTDlT8U7dAbrwqFUS+4tccyQFFr3p+0SjMaFcMhDkk/Gvrnf0ewt9T+EZMgfL30hHewidZrbZN8H7/ZTxhLbYNvLUTYNsXBa5tX5vXG02IwdNcazGNRGO/DAoGAYPGr+79+XiFq/yX67Uu6LqdNnmfqf5kfOSx9zTgRyxHY1OnA34T1yMnPz2iafM8/QJegVu89vy0dptBOV6mtKi/LvVSyqird6fhtjx4mlk8rX/ToAuWPxP11NqXoaJYb8igD1mvuKqP/67J6DXx3ECFGPD2qpN24Agms7EbzrPQ='
        #key = crypto.load_privatekey(type_, key)
        
        #cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(cert_path, 'rb').read())
        #key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(pkey_path, 'rb').read(), pkey_passphrase)

        #SignatureValue = base64.b64encode(signature).decode()
        # print '\n\n\n'
        # print 'signature: ', signature
        # print '\n\n\n'
        # print 'SignatureValue: ', SignatureValue
        # print '\n\n\n'
        # print 'error forzado: ', sssssss
        # return SignatureValue
        #return textwrap.fill( text, 64)


        
        # data_xml_SignatureValue_sha256 = hashlib.new('sha256', data_xml_SignedProperties_c14n)
        # data_xml_SignatureValue_digest = data_xml_SignedProperties_sha256.digest()
        # data_xml_SignatureValue_base = base64.b64encode(data_xml_SignedProperties_digest)
        return SignatureValue


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
        return file_name_zip


    def _generate_zip_content(self, FileNameXML, FileNameZIP, data_xml_document, document_repository):
        # Almacena archvio XML
        xml_file = document_repository +'/' + FileNameXML
        f = open (xml_file,'w')
        f.write(data_xml_document)
        f.close()
        # Comprime archvio XML
        zip_file = document_repository + '/' + FileNameZIP
        zf = zipfile.ZipFile(zip_file, mode="w")
        try:
            zf.write(xml_file, compress_type=compression)
        finally:
            zf.close()
        # Obtiene datos comprimidos
        data_xml = zip_file
        data_xml = open(data_xml,'r')
        data_xml = data_xml.read()
        contenido_data_xml_b64 = base64.b64encode(data_xml)


        # Ejemplo textwrap
        #prueba_textwrap = textwrap.fill(data_xml_document,64)

        # print '\n\n\n'
        # print 'prueba_textwrap: ', prueba_textwrap
        #xsd_file =  '/home/odoo/Instancias/9.0/odoo/backendevs/l10n_co_e-invoice/static/xsd/DIAN_UBL.xsd'
        #xsd_file =  '/home/odoo/Instancias/9.0/odoo/backendevs/l10n_co_e-invoice/static/xsd/DIAN_UBL_Structures.xsd'
        xsd_file =  '/home/odoo/Instancias/9.0/odoo/backendevs/l10n_co_e-invoice/static/xsd/xmldsig-core-schema.xsd'
        #xsd_file =  '/home/odoo/Instancias/9.0/odoo/backendevs/l10n_co_e-invoice/static/xsd/UBL-QualifiedDatatypes-2.0.xsd'
        # try:
        #     print '\n\n\n\n'
        #     print 'aaaaa'
        #     xmlschema_doc = etree.parse(xsd_file)
        #     print 'xmlschema_doc: ', xmlschema_doc 
        #     xmlschema = etree.XMLSchema(xmlschema_doc)
        #     print 'xmlschema: ', xmlschema
        #     xml_doc = etree.fromstring(data_xml_document.replace('\n',''))
        #     print 'xml_doc: ', xml_doc
        #     result = xmlschema.validate(xml_doc)
        #     print 'result: ', result
        #     if not result:
        #         xmlschema.assert_(xml_doc)
        #     return result
        # except AssertionError as e:
        #     _logger.warning(etree.tostring(xml_doc))
        #     raise UserError(_('XML Malformed Error:  %s') % e.args)

        # # #import xmlschema
        # xsd = etree.parse(xsd_file)
        # print '\n\n\n'
        # print 'xsd: ', xsd
        # print ''
        # xsd = etree.XMLSchema(xsd)
        # print '\n\n\n'
        # print 'xsd: ', xsd
        # print ''
        # #import xml.etree.ElementTree as ET
        # xml = etree.parse(data_xml_document)
        # print '\n\n\n'
        # print 'xml: ', xml
        # print ''
        # #result = xsd.is_valid(xml)
        # #print('Document is valid? {}'.format(result))
        # # xsd.validate(t)


        #Crypto
        # Obtiene la clave privada
        # key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(pkey_path, 'rb').read(), pkey_passphrase)
        # Obtiene la clave publica
        # pubkey = crypto.load_certificate(crypto.FILETYPE_PEM, key_pem)
        # Firma el documento con la clave privada
        # signature = crypto.sign(key,'data_xml_document','sha1')
        # Aplicar método de Canonicalización
        # data_xml_document = etree.tostring(etree.fromstring(data_xml_document), method="c14n")
        # print ''
        # print 'Paso 1'
        # key = 'uJhgwEK5U+TaL1PTd2YGejHC03MQaPIALiSrdY9D95bGAFNwsmkqlyIGSZUJ1Ha2rJ0L0275TOTAaUkTgu6NKNMrDnDByDrzVGWurmC14eXpnPMWXNuDq/CNge2AeZIOXIHxMsg6fzoLhlB6OWma2wsdbUnfKI6TeVYK0O1z9Kc='
        # cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(cert_path, 'rb').read())
        # pubkey = crypto.load_certificate(crypto.FILETYPE_PEM, key_pem)
        # key = crypto.load_privatekey(type_,privkey.encode('ascii'))
        # print ''
        # print 'key: ', key
        # signature = crypto.sign(key,'data_xml_document','sha1')
        # print ''
        # print 'signature: ', signature


        # if not given_message:
        #     common.print_error("Cannot sign blank message.")
        #     return None
        # # Sign the message by encrypting its hash with the private key:
        # try:
        #     signature = crypto.sign(given_key,given_message,'sha512')
        #     signature = base64.b64encode(signature)
        # except crypto.Error:
        #     common.print_error("Error signing message!")
        #     signature = ''
        # # Return signature:
        # return signature

        #String algorithmName = 'RSA';String key = 'pkcs8 format private key';Blob privateKey = EncodingUtil.base64Decode(key);Blob input = Blob.valueOf('12345qwerty');Crypto.sign(algorithmName, input, privateKey);

        # key = crypto.load_privatekey(type_, key)
        # signature = crypto.sign(key, texto, 'sha1')
        # text = base64.b64encode(signature).decode()
        # return textwrap.fill( text, 64)
        # key = load_pem_private_key(privkey.encode('ascii'), password=None, backend=default_backend())
        # key = crypto.load_privatekey(type_,privkey.encode('ascii'))
        # key = crypto.load_privatekey(type_, key)

        # key_pem = _to_bytes(key_pem)
        # if is_x509_cert:
        #     pubkey = crypto.load_certificate(crypto.FILETYPE_PEM, key_pem)
        # else:
        #     pubkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
        # return OpenSSLVerifier(pubkey) 

        return contenido_data_xml_b64


    @api.model
    def _generate_barcode(self, dian_constants, data_constants_document, CUFE, data_taxs):
        NumFac = data_constants_document['InvoiceID']
        FecFac = data_constants_document['IssueDateCufe']
        Time = data_constants_document['IssueTime']
        ValFac = data_constants_document['LineExtensionAmount']
        NitOFE = dian_constants['SupplierID']
        DocAdq = data_constants_document['CustomerID']
        ValFacIm = data_constants_document['PayableAmount']
        #FecFac = FecFac.replace('-','')+Time.replace(':','')
        ValIva = data_taxs['iva_01'] 
        ValOtroIm = data_taxs['ico_02'] + data_taxs['ica_03']   
        datos_qr = ' NumFac: '+NumFac+' FecFac: '+FecFac+' NitFac: '+NitOFE+' DocAdq: '+DocAdq+' ValFac: '+str(ValFac)+' ValIva: '+str(ValIva)+' ValOtroIm: '+str(ValOtroIm)+' ValFacIm: '+str(ValFacIm)+' CUFE: '+CUFE
        # Genera código QR
        qr_code = pyqrcode.create(datos_qr)
        qr_code = qr_code.png_as_base64_str(scale=2)
        # Genera el archivo png
        # qr_code = qr_code.png('qr-invoice.png')
        return qr_code


    @api.model
    def _generate_nonce(self, InvoiceID, seed_code):
        # NonceEncodingType # Se obtiene de 1. Calcular un valor aleatorio cuya semilla será definida y solamante conocida por el facturador electrónico y 2. Convertir a Base 64 el valor aleatorio obtenbido.
        # Ejemplo valor aleatorio.
        nonce = randint(1,seed_code)
        nonce = base64.b64encode(InvoiceID+str(nonce))
        # print '\n\n\n'
        # print 'nonce: ', nonce
        return nonce


    def _generate_software_security_code(self, software_identification_code, software_pin):
        software_security_code = hashlib.sha384(software_identification_code + software_pin)
        software_security_code = software_security_code.hexdigest()
        return  software_security_code 


    def _generate_datetime_created(self):
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        Created = now_bogota.strftime(fmt)[:-3]+'Z'
        #2015-07-31T16:34:33.762Z
        #2015-07-14T05:23:31
        return Created


    def _generate_datetime_IssueDate(self):
        date_invoice_cufe = {}
        fmtSend = "%Y-%m-%dT%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        date_invoice_cufe['IssueDateSend'] = now_bogota.strftime(fmtSend)
        fmtCUFE = "%Y%m%d%H%M%S"
        date_invoice_cufe['IssueDateCufe'] = now_bogota.strftime(fmtCUFE)
        fmtInvoice = "%Y-%m-%d"
        date_invoice_cufe['IssueDate'] = now_bogota.strftime(fmtInvoice)
        #2015-07-31T16:34:33.762Z
        #2015-07-14T05:23:31
        # print '\n\n\n\n'
        # print 'IssueDateSend: ',date_invoice_cufe['IssueDateSend']
        # print 'IssueDateCufe: ',date_invoice_cufe['IssueDateCufe']
        # print 'IssueDate: ',date_invoice_cufe['IssueDate']
        return date_invoice_cufe


    def _generate_xml_soap_request_validating_dian(self, by_validate_doc, dict_dian_constants):
        UserName = dict_dian_constants['Username']
        Password = dict_dian_constants['Password']
        #NitEmisor = dict_dian_constants['SupplierID']
        NitEmisor = dict_dian_constants['NitSinDV']
        IdentificadorSoftware = dict_dian_constants['SoftwareID']
        if by_validate_doc.document_type == 'f':
            TipoDocumento = '1'
        elif by_validate_doc.document_type == 'd':
            TipoDocumento = '2'
        else:
            TipoDocumento = '3'
        NumeroDocumento = by_validate_doc.dian_code
        FechaGeneracion = by_validate_doc.date_document_dian
        CUFE = by_validate_doc.cufe
        template_xml_soap_request_validating_dian = """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:con="http://www.dian.gov.co/servicios/facturaelectronica/ConsultaDocumentos">
<soapenv:Header>
<wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
<wsse:UsernameToken>
<wsse:Username>%(UserName)s</wsse:Username>
<wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">%(Password)s</wsse:Password>
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
</soapenv:Envelope>
"""

        #print "template_xml_soap_request_validating_dian:", template_xml_soap_request_validating_dian

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


    def _complements_second_decimal(self, amount):
        amount_dec = ((amount - int(amount)) * 100.0)
        amount_int = int(amount_dec)
        if  amount_int % 10 == 0:
            amount = str(amount) + '0'
        else: 
            amount = str(amount)
        return amount


    # def _template_signature_data_xml_id(self):
    #     # Id URI Falta anilizar si es con id distintos por xml
    #     template_signature_data_xml = """
    #             <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
    #             Id="%(IdSignature)s-Signature">
    #                 <ds:SignedInfo>
    #                     <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
    #                     <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
    #                     <ds:Reference Id="%(IdReference_zero)s-ref0" URI="">
    #                         <ds:Transforms>
    #                             <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
    #                         </ds:Transforms>
    #                         <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
    #                         <ds:DigestValue>%(data_xml_signature_ref_zero)s</ds:DigestValue>
    #                     </ds:Reference>
    #                     <ds:Reference URI="#%(URIReference_keyinfo)s-keyinfo">
    #                         <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
    #                         <ds:DigestValue>%(data_xml_keyinfo_base)s</ds:DigestValue>
    #                     </ds:Reference>
    #                     <ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#%(URIReference_signedprops)s-signedprops">
    #                         <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
    #                         <ds:DigestValue>%(data_xml_SignedProperties_base)s</ds:DigestValue>
    #                     </ds:Reference>
    #                 </ds:SignedInfo>
    #                 <ds:SignatureValue Id="%(IdSignatureValue)s-sigvalue">%(SignatureValue)s
    #                 </ds:SignatureValue>
    #                 <ds:KeyInfo Id="keyinfo">
    #                 <ds:KeyInfo Id="%(IdKeyInfo)s-keyinfo">
    #                     <ds:X509Data>
    #                         <ds:X509Certificate>%(data_public_certificate_base)s</ds:X509Certificate>
    #                     </ds:X509Data>
    #                 </ds:KeyInfo>
    #                 <ds:Object>
    #                     <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#%(Target)s">
    #                         <xades:SignedProperties Id="%(IdSignedProperties)s-signedprops">
    #                             <xades:SignedSignatureProperties>
    #                                 <xades:SigningTime>%(data_xml_SigningTime)s</xades:SigningTime>
    #                                 <xades:SigningCertificate>
    #                                     <xades:Cert>
    #                                         <xades:CertDigest>
    #                                             <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
    #                                             <ds:DigestValue>%(CertDigestDigestValue)s</ds:DigestValue>
    #                                         </xades:CertDigest>
    #                                         <xades:IssuerSerial>
    #                                             <ds:X509IssuerName>%(IssuerName)s</ds:X509IssuerName>
    #                                             <ds:X509SerialNumber>%(SerialNumber)s</ds:X509SerialNumber>
    #                                         </xades:IssuerSerial>
    #                                     </xades:Cert>
    #                                 </xades:SigningCertificate>
    #                                 <xades:SignaturePolicyIdentifier>
    #                                     <xades:SignaturePolicyId>
    #                                         <xades:SigPolicyId>
    #                                             <xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
    #                                         </xades:SigPolicyId>
    #                                         <xades:SigPolicyHash>
    #                                             <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
    #                                             <ds:DigestValue>%(data_xml_politics)s</ds:DigestValue>
    #                                         </xades:SigPolicyHash>
    #                                     </xades:SignaturePolicyId>
    #                                 </xades:SignaturePolicyIdentifier>
    #                                 <xades:SignerRole>
    #                                     <xades:ClaimedRoles>
    #                                         <xades:ClaimedRole>supplier</xades:ClaimedRole>
    #                                     </xades:ClaimedRoles>
    #                                 </xades:SignerRole>
    #                             </xades:SignedSignatureProperties>
    #                         </xades:SignedProperties>
    #                     </xades:QualifyingProperties>
    #                 </ds:Object>
    #             </ds:Signature>""" 
    #     return template_signature_data_xml 


    # @api.model
    # # Id URI Falta anilizar si es con id distintos por xml
    # def _update_signature_id(self, template_signature_data_xml, data_xml_document, 
    #                             data_xml_signature_ref_zero, data_public_certificate_base, 
    #                             data_xml_keyinfo_base, data_xml_politics, data_xml_SignedProperties_base, 
    #                             data_xml_SigningTime, dian_constants, data_constants_document,
    #                             data_xml_SignatureValue):
    #     data_xml_signature = template_signature_data_xml % {'data_xml_signature_ref_zero' : data_xml_signature_ref_zero,                                        
    #                                     'data_public_certificate_base' : data_public_certificate_base,
    #                                     'data_xml_keyinfo_base' : data_xml_keyinfo_base,
    #                                     'data_xml_politics' : data_xml_politics,
    #                                     'data_xml_SignedProperties_base' : data_xml_SignedProperties_base,
    #                                     'data_xml_SigningTime' : data_xml_SigningTime, 
    #                                     'CertDigestDigestValue' : dian_constants['CertDigestDigestValue'],
    #                                     'IssuerName' : dian_constants['IssuerName'], 
    #                                     'SerialNumber' : dian_constants['SerialNumber'],      
    #                                     'IdSignature' : data_constants_document['IdSignature'],
    #                                     'IdReference_zero' : data_constants_document['IdReference_zero'],
    #                                     'URIReference_keyinfo' : data_constants_document['URIReference_keyinfo'],
    #                                     'URIReference_signedprops' : data_constants_document['URIReference_signedprops'],
    #                                     'IdSignatureValue' : data_constants_document['IdSignatureValue'],
    #                                     'IdKeyInfo' : data_constants_document['IdKeyInfo'],
    #                                     'IdSignedProperties' : data_constants_document['IdSignedProperties'],
    #                                     'Target' : data_constants_document['Target'],
    #                                     'SignatureValue' : data_xml_SignatureValue,                               
    #                                     }
    #     return data_xml_signature

# Datos requeridos Nota de crédito
#   <ext:UBLExtension>
#       <ext:ExtensionContent>
#           <sts:DianExtensions>
#               <sts:InvoiceControl>
#           <ext:ExtensionContent>
#               <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-79c270e3-50bb-4fcf-b9bc-3a95bcf2466d">
#   UBLVersionID
#   ProfileID
#   ID
#   UUID
#   IssueDate
#   IssueTime
# Note # Notas sobre la Nota de Crédito (Opcional)
# DocumentCurrencyCode # Por lo que se ha analizado no va
# DiscrepancyResponse # Opcional Concepto de la nota de crédito
# BillingReference # Opcional
#   tns:AccountingSupplierPart   # Datos del facturador electronico
#   tns:AccountingCustomerParty # Datos del CLiente
#   tns:LegalMonetaryTotal
#   TaxTotal 
#   CreditNoteLine # 13.1.1 - Línea de Factura (nota crédito): Elemento que agrupa todos los campos de una línea de factura

#<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:rep="http://www.dian.gov.co/servicios/facturaelectronica/ReportarFactura">

#     def _template_send_header_xml(self):
#         template_send_data_xml = """<?xml version="1.0" encoding="UTF-8"?>
# <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:rep="http://www.dian.gov.co/servicios/facturaelectronica/ReportarFactura">
# <soapenv:Header>
# <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
# <wsse:UsernameToken>
# <wsse:Username>%(Username)s</wsse:Username>
# <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">%(Password)s</wsse:Password>
# <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">%(Nonce)s</wsse:Nonce>
# <wsu:Created>%(Created)s</wsu:Created>
# </wsse:UsernameToken>
# </wsse:Security>
# </soapenv:Header>
# </soapenv:Envelope>"""
#         return template_send_data_xml



# # </soapenv:Envelope>
#     def _template_send_body_xml(self):
#         template_send_body_xml = """<soapenv:Body>
# <rep:EnvioFacturaElectronicaPeticion>
# <rep:NIT>%(NIT)s</rep:NIT>
# <rep:InvoiceNumber>%(InvoiceNumber)s</rep:InvoiceNumber>
# <rep:IssueDate>%(IssueDate)s</rep:IssueDate>
# <rep:Document>%(Document)s</rep:Document>
# </rep:EnvioFacturaElectronicaPeticion>
# </soapenv:Body>"""
#         return template_send_body_xml


#     @api.model
#     def _generate_data_header_xml(self, template_send_header_xml, dian_constants, data_constants_document, 
#                                 Created, Document):
#         data_header_xml = template_send_header_xml % {'Username' : dian_constants['Username'],
#                         'Password' : dian_constants['Password'],
#                         'Nonce' : data_constants_document['Nonce'],
#                         'Created' : Created,
#                         }
#         return data_header_xml

#     @api.model
#     def _generate_data_body_xml(self, template_send_body_xml, dian_constants, data_constants_document, Document):
#         data_body_xml = template_send_body_xml % {'NIT' : data_constants_document['CustomerID'],
#                         'InvoiceNumber' : data_constants_document['InvoiceID'],
#                         'IssueDate' : data_constants_document['IssueDate'],
#                         'Document' : Document,
#                         }
#         return data_body_xml

            # prueba = client.factory.create('EnvioFacturaElectronica')
 
            # prueba.NIT = data_constants_document['CustomerID'] 
            # prueba.InvoiceNumber = data_constants_document['InvoiceID'] 
            # prueba.IssueDate = data_constants_document['IssueDate'] 
            # prueba.Document = ' '

            # template_send_header_xml = self._template_send_header_xml()
            # data_header_send = self._generate_data_header_xml(template_send_header_xml, dian_constants,data_constants_document, Created, Document)
            #client.set_options(soapheaders=data_header_send)

            #print '\n\n'
            #print 'client', client 
            #print 'prueba', prueba 
            #print 'data_header_send', data_header_send 
            #print ''
            # Username = usernameDIAN
            # Username = Element('wsse:Username').setText(dian_constants['Username'])
            # #Password = passwordDIAN
            # Password = Element('wsse:Password').setText(dian_constants['Password'])
            # Nonce = Element('wsse:Nonce').setText(data_constants_document['Nonce'])
            # Created = Element('wsse:Created').setText(Created)
            # header_list = [Username, Password, Nonce, Created]

            #client.set_options(soapheaders=data_header_send)



            # data_headers = etree.parse(data_xml_send)
            # data_headers = etree.fromstring(data_xml_send)
            # data_headers = etree.tostring(data_headers[0])
            # print '\n\n'
            # print 'data_headers: ', data_headers
            # print ''
            #data_headers = etree.tostring(etree.fromstring(data_headers), method="c14n")
            

            # Security = Element("wsse:Security")
            # UsernameToken = SubElement(Security,"wsse:UsernameToken")
            # SubElement(UsernameToken,"wsse:Username").text = dian_constants['Username']
            # SubElement(UsernameToken,"wsse:Password").text = dian_constants['Password']
            # SubElement(UsernameToken,"wsse:Nonce").text = data_constants_document['Nonce']
            # SubElement(UsernameToken,"wsu:Created").text = Created
            # client.set_options(soapheaders=Security)
            # NIT = data_constants_document['CustomerID'] 
            # InvoiceNumber = data_constants_document['InvoiceID'] 
            # IssueDate = data_constants_document['IssueDate'] 
            #Document = ' '
            #response = client.service.EnvioFacturaElectronica(prueba)
            # from suds import byte_str
            #message = byte_str(data_xml_send)

            # response = client.service.EnvioFacturaElectronica(__inject={'msg': message})

            #response = client.service.EnvioFacturaElectronica()
            #response = client.service.EnvioFacturaElectronica(__inject={'msg' : data_xml_send})
            #message = byte_str(response)
            # Respuesta DIAN
            # print ''
            # print 'response', response 
            # print 'message', message
            # print ''
            #Arreglo encabezados
            # encabezado = [{ "Username" : dian_constants['Username'], 
            #                 "Password" : dian_constants['Password'],
            #                 "Nonce" : data_constants_document['Nonce'],
            #                 "Created" : Created,
            #             }]
            # cuerpo =  [{    "NIT" : data_constants_document['CustomerID'], 
            #                 "InvoiceNumber" : data_constants_document['InvoiceID'],
            #                 "IssueDate" : data_constants_document['IssueDate'],
            #                 "Document" : Document,
            #             }]
                        # cuerpo =  [{    "NIT" : data_constants_document['CustomerID'], 
            #                 "InvoiceNumber" : data_constants_document['InvoiceID'],
            #                 "IssueDate" : data_constants_document['IssueDate'],
            #                 "Document" : Document,
            #             }]


                        # cuerpo =  [{    "NIT" : data_constants_document['CustomerID'], 
            #                 "InvoiceNumber" : data_constants_document['InvoiceID'],
            #                 "IssueDate" : data_constants_document['IssueDate'],
            #                 "Document" : Document,
            #             }]


            # prueba = client.factory.create('EnvioFacturaElectronica')
 
            # prueba.NIT = data_constants_document['CustomerID'] 
            # prueba.InvoiceNumber = data_constants_document['InvoiceID'] 
            # prueba.IssueDate = data_constants_document['IssueDate'] 
            # prueba.Document = ' '
    # Error semantico
    #<wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">

#pem = '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'
#pem = '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'
#pem = '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'
#        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

    @api.model    
    def _prueba_manual_xml(self):
        # Notas
        # 1.- Id xmldsig
        # 2.- xmlns:
        # 2.- Keyinfo con mas datos x509
        # 3.- XML codificación UTF-8
        #
        # referencia 0 digest del documento
        xml_sin_firma = """<?xml version="1.0" encoding="UTF-8"?><fe:Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:clm54217="urn:un:unece:uncefact:codelist:specification:54217:2001" xmlns:clm66411="urn:un:unece:uncefact:codelist:specification:66411:2001" xmlns:clmIANAMIMEMediaType="urn:un:unece:uncefact:codelist:specification:IANAMIMEMediaType:2003" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xmlns:qdt="urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:udt="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.dian.gov.co/contratos/facturaelectronica/v1 http://www.dian.gov.co/micrositios/fac_electronica/documentos/XSD/r0/DIAN_UBL.xsd urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2 http://www.dian.gov.co/micrositios/fac_electronica/documentos/common/UnqualifiedDataTypeSchemaModule-2.0.xsd urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2 http://www.dian.gov.co/micrositios/fac_electronica/documentos/common/UBL-QualifiedDatatypes-2.0.xsd"><ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent><sts:DianExtensions><sts:InvoiceControl><sts:InvoiceAuthorization>9000000032442243</sts:InvoiceAuthorization><sts:AuthorizationPeriod><cbc:StartDate>2018-10-03</cbc:StartDate><cbc:EndDate>2018-12-31</cbc:EndDate></sts:AuthorizationPeriod><sts:AuthorizedInvoices><sts:Prefix>PRUE</sts:Prefix><sts:From>980000000</sts:From><sts:To>985000000</sts:To></sts:AuthorizedInvoices></sts:InvoiceControl><sts:InvoiceSource><cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.0">CO</cbc:IdentificationCode></sts:InvoiceSource><sts:SoftwareProvider><sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">860062288</sts:ProviderID><sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">b28bc5bb-8a74-46a7-bb16-d3e25ca58358</sts:SoftwareID></sts:SoftwareProvider><sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">8a1a3aefcb472f961dbd803770001520f4e4a764d850d150bef9d6173a3d13ded68513092639a767aa76e6fb233bbc71</sts:SoftwareSecurityCode></sts:DianExtensions></ext:ExtensionContent></ext:UBLExtension><ext:UBLExtension><ext:ExtensionContent></ext:ExtensionContent></ext:UBLExtension></ext:UBLExtensions><cbc:UBLVersionID>UBL 2.0</cbc:UBLVersionID><cbc:ProfileID>DIAN 1.0</cbc:ProfileID><cbc:ID>PRUE980000117</cbc:ID><cbc:UUID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">963f8f248afe8ae9888acc4594c12804544b8355</cbc:UUID><cbc:IssueDate>2018-10-22</cbc:IssueDate><cbc:IssueTime>16:42:03</cbc:IssueTime><cbc:InvoiceTypeCode listAgencyID="195" listAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" listSchemeURI="http://www.dian.gov.co/contratos/facturaelectronica/v1/InvoiceType">1</cbc:InvoiceTypeCode><cbc:Note></cbc:Note><cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode><fe:AccountingSupplierParty><cbc:AdditionalAccountID>2</cbc:AdditionalAccountID><fe:Party><cac:PartyIdentification><cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="31">860062288</cbc:ID></cac:PartyIdentification><cac:PartyName><cbc:Name>Plastinorte S.A.S</cbc:Name></cac:PartyName><fe:PhysicalLocation><fe:Address><cbc:Department>BOGOTA, D.C.</cbc:Department><cbc:CitySubdivisionName>BOGOTA</cbc:CitySubdivisionName><cbc:CityName>BOGOTA</cbc:CityName><cac:AddressLine><cbc:Line>Cra. 25 #67-34</cbc:Line></cac:AddressLine><cac:Country><cbc:IdentificationCode>CO</cbc:IdentificationCode></cac:Country></fe:Address></fe:PhysicalLocation><fe:PartyTaxScheme><cbc:TaxLevelCode>7</cbc:TaxLevelCode><cac:TaxScheme></cac:TaxScheme></fe:PartyTaxScheme><fe:PartyLegalEntity><cbc:RegistrationName>Plastinorte S.A.S</cbc:RegistrationName></fe:PartyLegalEntity><cac:Contact><cbc:Telephone></cbc:Telephone><cbc:ElectronicMail></cbc:ElectronicMail></cac:Contact></fe:Party></fe:AccountingSupplierParty><fe:AccountingCustomerParty><cbc:AdditionalAccountID>2</cbc:AdditionalAccountID><fe:Party><cac:PartyIdentification><cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="31">900979979</cbc:ID></cac:PartyIdentification><cac:PartyName><cbc:Name>2  SH</cbc:Name></cac:PartyName><fe:PhysicalLocation><fe:Address><cbc:Department>BOGOTA, D.C.</cbc:Department><cbc:CitySubdivisionName>BOGOTA</cbc:CitySubdivisionName><cbc:CityName>BOGOTA</cbc:CityName><cac:AddressLine><cbc:Line>cll 12 a # 71 b 61</cbc:Line></cac:AddressLine><cac:Country><cbc:IdentificationCode>CO</cbc:IdentificationCode></cac:Country></fe:Address></fe:PhysicalLocation><fe:PartyTaxScheme><cbc:TaxLevelCode>False</cbc:TaxLevelCode><cac:TaxScheme></cac:TaxScheme></fe:PartyTaxScheme><fe:PartyLegalEntity><cbc:RegistrationName>2  SH</cbc:RegistrationName></fe:PartyLegalEntity></fe:Party></fe:AccountingCustomerParty><fe:TaxTotal><cbc:TaxAmount currencyID="COP">2280.00</cbc:TaxAmount><cbc:TaxEvidenceIndicator>true</cbc:TaxEvidenceIndicator><fe:TaxSubtotal><cbc:TaxableAmount currencyID="COP">12000.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="COP">2280.00</cbc:TaxAmount><cbc:Percent>19.00</cbc:Percent><cac:TaxCategory><cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme></cac:TaxCategory></fe:TaxSubtotal></fe:TaxTotal><fe:TaxTotal><cbc:TaxAmount currencyID="COP">-48.00</cbc:TaxAmount><cbc:TaxEvidenceIndicator>true</cbc:TaxEvidenceIndicator><fe:TaxSubtotal><cbc:TaxableAmount currencyID="COP">0.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="COP">-48.00</cbc:TaxAmount><cbc:Percent>-1.1040</cbc:Percent><cac:TaxCategory><cac:TaxScheme><cbc:ID>02</cbc:ID></cac:TaxScheme></cac:TaxCategory></fe:TaxSubtotal></fe:TaxTotal><fe:TaxTotal><cbc:TaxAmount currencyID="COP">-132.00</cbc:TaxAmount><cbc:TaxEvidenceIndicator>true</cbc:TaxEvidenceIndicator><fe:TaxSubtotal><cbc:TaxableAmount currencyID="COP">0.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="COP">-132.00</cbc:TaxAmount><cbc:Percent>-1.1040</cbc:Percent><cac:TaxCategory><cac:TaxScheme><cbc:ID>03</cbc:ID></cac:TaxScheme></cac:TaxCategory></fe:TaxSubtotal></fe:TaxTotal><fe:LegalMonetaryTotal><cbc:LineExtensionAmount currencyID="COP">12000.00</cbc:LineExtensionAmount><cbc:TaxExclusiveAmount currencyID="COP">12000.00</cbc:TaxExclusiveAmount><cbc:TaxInclusiveAmount currencyID="COP">0.00</cbc:TaxInclusiveAmount><cbc:AllowanceTotalAmount currencyID="COP">0.00</cbc:AllowanceTotalAmount><cbc:ChargeTotalAmount currencyID="COP">0.00</cbc:ChargeTotalAmount><cbc:PrepaidAmount currencyID="COP">0.00</cbc:PrepaidAmount><cbc:PayableAmount currencyID="COP">14280.00</cbc:PayableAmount></fe:LegalMonetaryTotal><fe:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity>1.00</cbc:InvoicedQuantity><cbc:LineExtensionAmount currencyID="COP">12000.00</cbc:LineExtensionAmount><cac:AllowanceCharge><cbc:ChargeIndicator>true</cbc:ChargeIndicator><cbc:Amount currencyID="COP">0.00</cbc:Amount></cac:AllowanceCharge><fe:Item><cbc:Description>[AC-AL-7] Almohada En Fibra</cbc:Description></fe:Item><fe:Price><cbc:PriceAmount currencyID="COP">14280.00</cbc:PriceAmount></fe:Price></fe:InvoiceLine></fe:Invoice>"""
        xml_sin_firma = xml_sin_firma.replace('\n','')
        xml_sin_firma = etree.tostring(etree.fromstring(xml_sin_firma), method="c14n")
        print '\n\n\n'
        print 'xml_sin_firma: ', xml_sin_firma
        refa = hashlib.new('sha256', xml_sin_firma)
        refa = refa.digest()
        refa = base64.b64encode(refa)
        print '\n\n\n'
        print 'refa: ', refa
        #
        # referencia 1 o digest de keyinfo
        #clave_publica = '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'
        clave_publica = """-----BEGIN CERTIFICATE-----
MIIIZjCCBk6gAwIBAgIIZs5T/GUfuWowDQYJKoZIhvcNAQELBQAwgbQxIzAhBgkq
hkiG9w0BCQEWFGluZm9AYW5kZXNzY2QuY29tLmNvMSMwIQYDVQQDExpDQSBBTkRF
UyBTQ0QgUy5BLiBDbGFzZSBJSTEwMC4GA1UECxMnRGl2aXNpb24gZGUgY2VydGlm
aWNhY2lvbiBlbnRpZGFkIGZpbmFsMRMwEQYDVQQKEwpBbmRlcyBTQ0QuMRQwEgYD
VQQHEwtCb2dvdGEgRC5DLjELMAkGA1UEBhMCQ08wHhcNMTgxMDAxMjM0NzAwWhcN
MjAwOTMwMjM0NjAwWjCCAR8xFjAUBgNVBAkTDUNyYS4gMjUgNjctMzQxJjAkBgkq
hkiG9w0BCQEWF2RvbWluaWNAcGxhc3Rpbm9ydGUuY29tMRowGAYDVQQDExFQTEFT
VElOT1JURSBTLkEuUzETMBEGA1UEBRMKODYwMDYyMjg4MTE2MDQGA1UEDBMtRW1p
c29yIEZhY3R1cmEgRWxlY3Ryb25pY2EgLSBQZXJzb25hIEp1cmlkaWNhMSswKQYD
VQQLEyJFbWl0aWRvIHBvciBBbmRlcyBTQ0QgQ3JhIDI3IDg2IDQzMRIwEAYDVQQK
EwlMb2dpc3RpY2ExDzANBgNVBAcTBkJPR09UQTEVMBMGA1UECBMMQ1VORElOQU1B
UkNBMQswCQYDVQQGEwJDTzCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEB
AJhLhTEW+9aAZFO/WE38q4JAMnSr17z1CFlM0oYITmdCmEAyuTFBL81GRTMw1aYu
VHOY4dGeMgfeXKhhH7oIwOSsZiwcoe41N0OeW4O571RMZU0/wqkcywzA99UsODwx
wnj6leFyCmTIMLxxKI3uXYJuscryPCjkLTFaf73wedz/uy6A1tLNlb4dGBP0wUE8
p9Ht3yeNzs0p0eu5KDKUJoK4tJ3TSM07JUVT90BDCgQzhVsF4p+h7KwI6zXA6jlU
qdnt4VWD8ppQwX2Nrw+eoylYi9jFdgO2B+nBVUCW35qlYDy4LQVNJMaYMWeYfek+
VXxU9Hv0NbiEY54ctpVsyMUCAwEAAaOCAwwwggMIMAwGA1UdEwEB/wQCMAAwHwYD
VR0jBBgwFoAUqEu09AuntlvUoCiFEJ0EEzPEp/cwNwYIKwYBBQUHAQEEKzApMCcG
CCsGAQUFBzABhhtodHRwOi8vb2NzcC5hbmRlc3NjZC5jb20uY28wIgYDVR0RBBsw
GYEXZG9taW5pY0BwbGFzdGlub3J0ZS5jb20wggHxBgNVHSAEggHoMIIB5DCCAeAG
DSsGAQQBgfRIAQIGAQIwggHNMEEGCCsGAQUFBwIBFjVodHRwOi8vd3d3LmFuZGVz
c2NkLmNvbS5jby9kb2NzL0RQQ19BbmRlc1NDRF9WMy4wLnBkZjCCAYYGCCsGAQUF
BwICMIIBeB6CAXQATABhACAAdQB0AGkAbABpAHoAYQBjAGkA8wBuACAAZABlACAA
ZQBzAHQAZQAgAGMAZQByAHQAaQBmAGkAYwBhAGQAbwAgAGUAcwB0AOEAIABzAHUA
agBlAHQAYQAgAGEAIABsAGEAcwAgAFAAbwBsAO0AdABpAGMAYQBzACAAZABlACAA
QwBlAHIAdABpAGYAaQBjAGEAZABvACAAZABlACAARgBhAGMAdAB1AHIAYQBjAGkA
8wBuACAARQBsAGUAYwB0AHIA8wBuAGkAYwBhACAAKABQAEMAKQAgAHkAIABEAGUA
YwBsAGEAcgBhAGMAaQDzAG4AIABkAGUAIABQAHIA4QBjAHQAaQBjAGEAcwAgAGQA
ZQAgAEMAZQByAHQAaQBmAGkAYwBhAGMAaQDzAG4AIAAoAEQAUABDACkAIABlAHMA
dABhAGIAbABlAGMAaQBkAGEAcwAgAHAAbwByACAAQQBuAGQAZQBzACAAUwBDAEQw
HQYDVR0lBBYwFAYIKwYBBQUHAwIGCCsGAQUFBwMEMDcGA1UdHwQwMC4wLKAqoCiG
Jmh0dHA6Ly9jcmwuYW5kZXNzY2QuY29tLmNvL0NsYXNlSUkuY3JsMB0GA1UdDgQW
BBT9KK2K/nR0uYamAIaZ2GBorHuYDDAOBgNVHQ8BAf8EBAMCBeAwDQYJKoZIhvcN
AQELBQADggIBAK3bCKg27fRL7v3MYqHdxvm84D1mCzE3RzfFCK3ujpoIuTSZcsfV
/OEuYV+n8fgFSVqbOANU3reqnm83ZQOLrWhfF4gOJqH0tbQh66SfH53m9svd/8Dr
oTi/1jBYCL4QZKWXWC41htWIxOBc1BLoFwe9gtSI6zGFQACTIXClWxoN+aa7RXwR
kDB8UsMpbblZukO4RUjCKzOXLaDUaZZR7cD3HGlFzZIARU+OC+qL5YLhuUp45jJ/
KlK2X28sH6ikgJr4JOqwg7I0G/32Kdqf403J5oNUtcSRUeQp0LkHX/9oq1rXuwLq
71t7bpfFlIbDHrkx8TcDpXYC61EYeHaPihMDMkn+RKDNemfAoMvnLfpScZv5LHPZ
oj2AcpJL7M43KuHDkXLxlMpCJZtLsGWOD3+knh6JqvKZAJ/Yo7pk6ZZRRMHiM0Ie
/nwVSe7kSiPv7rCf/Q0WLVntoyar4sxlHb/ojq9mDcA19nehkSWCk4azZY/b8lJK
zeucAgmP9e2Uq6lm6zxOfcayHwdVTyXCLANwLHGeEUh/b1shkI3BmruLRrfz6lOj
0uY/WhhKmjYGzST906iua2X0BoxfRYujQ0ey+mjIP7HyoRTK5T0WS0JusIfOEG4q
RRZw04bG19spiLKEz8ZK4OYQ69zdBgou9Zlz0co57fWqWXrSql2i1u8v
-----END CERTIFICATE-----"""
        clave_publica_64 = base64.b64encode(clave_publica) 
        #<ds:KeyInfo Id="xmldsig-87d128b5-aa31-4f0b-8e45-3d9cfa0eec26-keyinfo">
        keyinfo = """<ds:KeyInfo xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Id="xmldsig-87d128b5-aa31-4f0b-8e45-3d9cfa0eec26-keyinfo">
<ds:X509Data>
<ds:X509Certificate>%(data_public_certificate_base)s</ds:X509Certificate>
</ds:X509Data>
</ds:KeyInfo>"""
        keyinfo = keyinfo % {'data_public_certificate_base' : clave_publica_64,}
        keyinfo = keyinfo.replace('\n','')
        keyinfo = etree.tostring(etree.fromstring(keyinfo), method="c14n")
        print '\n\n\n'
        print 'keyinfo: ', keyinfo
        refb = hashlib.new('sha256', keyinfo)
        refb = refb.digest()
        refb = base64.b64encode(refb)
        print '\n\n\n'
        print 'refb: ', refb
        #
        # referencia 2 o digest de signedproperties
        CertDigestDigestValue256 = hashlib.new('sha256', clave_publica)
        CertDigestDigestValue256_digest = CertDigestDigestValue256.digest()
        CertDigestDigestValue = base64.b64encode(CertDigestDigestValue256_digest)
        #SigningTime = self._generate_signature_signingtime()
        SigningTime = '2018-10-23T15:07:11'
        print '\n\n\n'
        print 'CertDigestDigestValue: ', CertDigestDigestValue
        print 'SigningTime: ', SigningTime
        signedproperties = """
<xades:SignedProperties xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-signedprops">
<xades:SignedSignatureProperties>
<xades:SigningTime>%(SigningTime)s</xades:SigningTime>
<xades:SigningCertificate>
<xades:Cert>
<xades:CertDigest>
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>vktY2yPIu12GrUgajtIBfu3XviglFFewq9wXt57bBCE=</ds:DigestValue>
</xades:CertDigest>
<xades:IssuerSerial>
<ds:X509IssuerName>C=CO, L=Bogota D.C., O=Andes SCD., OU=Division de certificacion entidad final, CN=CA ANDES SCD S.A. Clase II, E=info@andesscd.com.co</ds:X509IssuerName>
<ds:X509SerialNumber>7407950780564486506</ds:X509SerialNumber>
</xades:IssuerSerial>
</xades:Cert>
</xades:SigningCertificate>
<xades:SignaturePolicyIdentifier>
<xades:SignaturePolicyId>
<xades:SigPolicyId>
<xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
</xades:SigPolicyId>
<xades:SigPolicyHash>
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>%(CertDigestDigestValue)s</ds:DigestValue>
</xades:SigPolicyHash>
</xades:SignaturePolicyId>
</xades:SignaturePolicyIdentifier>
<xades:SignerRole>
<xades:ClaimedRoles>
<xades:ClaimedRole>supplier</xades:ClaimedRole>
</xades:ClaimedRoles>
</xades:SignerRole>
</xades:SignedSignatureProperties>
</xades:SignedProperties>"""
        signedproperties = signedproperties % {'SigningTime' : SigningTime,
                                                'CertDigestDigestValue' : CertDigestDigestValue,}
        signedproperties = signedproperties.replace('\n','')
        signedproperties = etree.tostring(etree.fromstring(signedproperties), method="c14n")
        print '\n\n\n'
        print 'signedproperties: ', signedproperties
        refc = hashlib.new('sha256', signedproperties)
        refc = refc.digest()
        refc = base64.b64encode(refc)
        print '\n\n\n'
        print 'refc: ', refc
        #
        # SignedInfo en donde va la refa, la refb y la refc y obtener el signaturevalue.
        SignedInfo = """
<ds:SignedInfo xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
<ds:Reference Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-ref0" URI="">
<ds:Transforms>
<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
</ds:Transforms>
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>%(refa)s</ds:DigestValue>
</ds:Reference>
<ds:Reference URI="#xmldsig-87d128b5-aa31-4f0b-8e45-3d9cfa0eec26-keyinfo">
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>%(refb)s</ds:DigestValue>
</ds:Reference>
<ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-signedprops">
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>%(refc)s</ds:DigestValue>
</ds:Reference>
</ds:SignedInfo>
"""
        SignedInfo = SignedInfo % {'refa' : refa,
                                    'refb' : refb,
                                    'refc' : refc,}
        SignedInfo = SignedInfo.replace('\n','')
        SignedInfo = etree.tostring(etree.fromstring(SignedInfo), method="c14n")
        #SignedInfo = etree.tostring(SignedInfo,method="c14n",exclusive=False,with_comments=False,inclusive_ns_prefixes=None)
        #SignedInfo = SignedInfo.decode()
        print '\n\n\n'
        print 'SignedInfo: ', SignedInfo
        #archivo_key = '/tmp/Certificado/plastinorte.com.key'
        archivo_key = '/home/odoo/Instancias/DocumentosFE/Clave3.pem'
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(archivo_key, 'rb').read())
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_key, 'rb').read())
        signature = crypto.sign(key, SignedInfo, 'sha256')
        #archivo_pem = '/tmp/Certificado/744524.pem' 
        archivo_pem = '/home/odoo/Instancias/DocumentosFE/Clave3.pem' 
        pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        validacion = crypto.verify(pem, signature, SignedInfo, 'sha256')

        # passa = ''
        # p12 = crypto.load_pkcs12('/tmp/Certificado/744524.pem', passa)
        # acert = p12.get_certificate()
        # aprivky = p12.get_privatekey()
        # acacert = p12.get_ca_certificates()
        # aissuer = cert.get_issuer()
        # asubject = cert.get_subject()


        print '\n\n\n\n\n\n'
        print 'pem: ', pem
        print 'key: ', key
        print 'cert: ', cert
        print 'validacion: ', validacion
        SignatureValue = base64.b64encode(signature)
        print '\n\n\n'
        print 'SignatureValue: ', SignatureValue
        #
        # SIGNATURE.
        Signature_xlm = """
<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5">
%(SignedInfo)s
<ds:SignatureValue Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-sigvalue">%(SignatureValue)s</ds:SignatureValue>
%(Keyinfo)s
<ds:Object>
<xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5">
%(signedproperties)s
</xades:QualifyingProperties>
</ds:Object>
</ds:Signature>""" 
        Signature_xlm = Signature_xlm % {'SignedInfo' : SignedInfo,
                                    'SignatureValue' : SignatureValue,
                                    'Keyinfo' : keyinfo,
                                    'signedproperties' : signedproperties,}
        print '\n\n\n'
        print 'Signature_xlm: ', Signature_xlm
        xml_con_firma = """<?xml version="1.0" encoding="UTF-8"?><fe:Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:clm54217="urn:un:unece:uncefact:codelist:specification:54217:2001" xmlns:clm66411="urn:un:unece:uncefact:codelist:specification:66411:2001" xmlns:clmIANAMIMEMediaType="urn:un:unece:uncefact:codelist:specification:IANAMIMEMediaType:2003" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xmlns:qdt="urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:udt="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.dian.gov.co/contratos/facturaelectronica/v1 http://www.dian.gov.co/micrositios/fac_electronica/documentos/XSD/r0/DIAN_UBL.xsd urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2 http://www.dian.gov.co/micrositios/fac_electronica/documentos/common/UnqualifiedDataTypeSchemaModule-2.0.xsd urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2 http://www.dian.gov.co/micrositios/fac_electronica/documentos/common/UBL-QualifiedDatatypes-2.0.xsd"><ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent><sts:DianExtensions><sts:InvoiceControl><sts:InvoiceAuthorization>9000000032442243</sts:InvoiceAuthorization><sts:AuthorizationPeriod><cbc:StartDate>2018-10-03</cbc:StartDate><cbc:EndDate>2018-12-31</cbc:EndDate></sts:AuthorizationPeriod><sts:AuthorizedInvoices><sts:Prefix>PRUE</sts:Prefix><sts:From>980000000</sts:From><sts:To>985000000</sts:To></sts:AuthorizedInvoices></sts:InvoiceControl><sts:InvoiceSource><cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.0">CO</cbc:IdentificationCode></sts:InvoiceSource><sts:SoftwareProvider><sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">860062288</sts:ProviderID><sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">b28bc5bb-8a74-46a7-bb16-d3e25ca58358</sts:SoftwareID></sts:SoftwareProvider><sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">8a1a3aefcb472f961dbd803770001520f4e4a764d850d150bef9d6173a3d13ded68513092639a767aa76e6fb233bbc71</sts:SoftwareSecurityCode></sts:DianExtensions></ext:ExtensionContent></ext:UBLExtension><ext:UBLExtension><ext:ExtensionContent>%(SignatureFin)s</ext:ExtensionContent></ext:UBLExtension></ext:UBLExtensions><cbc:UBLVersionID>UBL 2.0</cbc:UBLVersionID><cbc:ProfileID>DIAN 1.0</cbc:ProfileID><cbc:ID>PRUE980000117</cbc:ID><cbc:UUID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">963f8f248afe8ae9888acc4594c12804544b8355</cbc:UUID><cbc:IssueDate>2018-10-22</cbc:IssueDate><cbc:IssueTime>16:42:03</cbc:IssueTime><cbc:InvoiceTypeCode listAgencyID="195" listAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" listSchemeURI="http://www.dian.gov.co/contratos/facturaelectronica/v1/InvoiceType">1</cbc:InvoiceTypeCode><cbc:Note></cbc:Note><cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode><fe:AccountingSupplierParty><cbc:AdditionalAccountID>2</cbc:AdditionalAccountID><fe:Party><cac:PartyIdentification><cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="31">860062288</cbc:ID></cac:PartyIdentification><cac:PartyName><cbc:Name>Plastinorte S.A.S</cbc:Name></cac:PartyName><fe:PhysicalLocation><fe:Address><cbc:Department>BOGOTA, D.C.</cbc:Department><cbc:CitySubdivisionName>BOGOTA</cbc:CitySubdivisionName><cbc:CityName>BOGOTA</cbc:CityName><cac:AddressLine><cbc:Line>Cra. 25 #67-34</cbc:Line></cac:AddressLine><cac:Country><cbc:IdentificationCode>CO</cbc:IdentificationCode></cac:Country></fe:Address></fe:PhysicalLocation><fe:PartyTaxScheme><cbc:TaxLevelCode>7</cbc:TaxLevelCode><cac:TaxScheme></cac:TaxScheme></fe:PartyTaxScheme><fe:PartyLegalEntity><cbc:RegistrationName>Plastinorte S.A.S</cbc:RegistrationName></fe:PartyLegalEntity><cac:Contact><cbc:Telephone></cbc:Telephone><cbc:ElectronicMail></cbc:ElectronicMail></cac:Contact></fe:Party></fe:AccountingSupplierParty><fe:AccountingCustomerParty><cbc:AdditionalAccountID>2</cbc:AdditionalAccountID><fe:Party><cac:PartyIdentification><cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="31">900979979</cbc:ID></cac:PartyIdentification><cac:PartyName><cbc:Name>2  SH</cbc:Name></cac:PartyName><fe:PhysicalLocation><fe:Address><cbc:Department>BOGOTA, D.C.</cbc:Department><cbc:CitySubdivisionName>BOGOTA</cbc:CitySubdivisionName><cbc:CityName>BOGOTA</cbc:CityName><cac:AddressLine><cbc:Line>cll 12 a # 71 b 61</cbc:Line></cac:AddressLine><cac:Country><cbc:IdentificationCode>CO</cbc:IdentificationCode></cac:Country></fe:Address></fe:PhysicalLocation><fe:PartyTaxScheme><cbc:TaxLevelCode>False</cbc:TaxLevelCode><cac:TaxScheme></cac:TaxScheme></fe:PartyTaxScheme><fe:PartyLegalEntity><cbc:RegistrationName>2  SH</cbc:RegistrationName></fe:PartyLegalEntity></fe:Party></fe:AccountingCustomerParty><fe:TaxTotal><cbc:TaxAmount currencyID="COP">2280.00</cbc:TaxAmount><cbc:TaxEvidenceIndicator>true</cbc:TaxEvidenceIndicator><fe:TaxSubtotal><cbc:TaxableAmount currencyID="COP">12000.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="COP">2280.00</cbc:TaxAmount><cbc:Percent>19.00</cbc:Percent><cac:TaxCategory><cac:TaxScheme><cbc:ID>01</cbc:ID></cac:TaxScheme></cac:TaxCategory></fe:TaxSubtotal></fe:TaxTotal><fe:TaxTotal><cbc:TaxAmount currencyID="COP">-48.00</cbc:TaxAmount><cbc:TaxEvidenceIndicator>true</cbc:TaxEvidenceIndicator><fe:TaxSubtotal><cbc:TaxableAmount currencyID="COP">0.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="COP">-48.00</cbc:TaxAmount><cbc:Percent>-1.1040</cbc:Percent><cac:TaxCategory><cac:TaxScheme><cbc:ID>02</cbc:ID></cac:TaxScheme></cac:TaxCategory></fe:TaxSubtotal></fe:TaxTotal><fe:TaxTotal><cbc:TaxAmount currencyID="COP">-132.00</cbc:TaxAmount><cbc:TaxEvidenceIndicator>true</cbc:TaxEvidenceIndicator><fe:TaxSubtotal><cbc:TaxableAmount currencyID="COP">0.00</cbc:TaxableAmount><cbc:TaxAmount currencyID="COP">-132.00</cbc:TaxAmount><cbc:Percent>-1.1040</cbc:Percent><cac:TaxCategory><cac:TaxScheme><cbc:ID>03</cbc:ID></cac:TaxScheme></cac:TaxCategory></fe:TaxSubtotal></fe:TaxTotal><fe:LegalMonetaryTotal><cbc:LineExtensionAmount currencyID="COP">12000.00</cbc:LineExtensionAmount><cbc:TaxExclusiveAmount currencyID="COP">12000.00</cbc:TaxExclusiveAmount><cbc:TaxInclusiveAmount currencyID="COP">0.00</cbc:TaxInclusiveAmount><cbc:AllowanceTotalAmount currencyID="COP">0.00</cbc:AllowanceTotalAmount><cbc:ChargeTotalAmount currencyID="COP">0.00</cbc:ChargeTotalAmount><cbc:PrepaidAmount currencyID="COP">0.00</cbc:PrepaidAmount><cbc:PayableAmount currencyID="COP">14280.00</cbc:PayableAmount></fe:LegalMonetaryTotal><fe:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity>1.00</cbc:InvoicedQuantity><cbc:LineExtensionAmount currencyID="COP">12000.00</cbc:LineExtensionAmount><cac:AllowanceCharge><cbc:ChargeIndicator>true</cbc:ChargeIndicator><cbc:Amount currencyID="COP">0.00</cbc:Amount></cac:AllowanceCharge><fe:Item><cbc:Description>[AC-AL-7] Almohada En Fibra</cbc:Description></fe:Item><fe:Price><cbc:PriceAmount currencyID="COP">14280.00</cbc:PriceAmount></fe:Price></fe:InvoiceLine></fe:Invoice>"""
        xml_con_firma = xml_con_firma.replace('\n','')
        xml_con_firma = etree.tostring(etree.fromstring(xml_con_firma), method="c14n")
        xml_con_firma = xml_con_firma % {'SignatureFin' : Signature_xlm,}        
        print '\n\n\n'
        print 'xml_con_firma: ', xml_con_firma
        return xml_con_firma

#         xml_otro = """<?xml version="1.0" encoding="UTF-8"?>
#         <fe:Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cacadd="urn:e-billing:aggregates" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:cbcadd="urn:e-billing:basics" xmlns:clm54217="urn:un:unece:uncefact:codelist:specification:54217:2001" xmlns:clm66411="urn:un:unece:uncefact:codelist:specification:66411:2001" xmlns:clmIANAMIMEMediaType="urn:un:unece:uncefact:codelist:specification:IANAMIMEMediaType:2003" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:extadd="urn:e-billing:extension" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xmlns:qdt="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:udt="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.dian.gov.co/contratos/facturaelectronica/v1 ../xsd/DIAN_UBL.xsd urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2 ../../ubl2/common/UnqualifiedDataTypeSchemaModule-2.0.xsd urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2 ../../ubl2/common/UBL-QualifiedDatatypes-2.0.xsd">
# <ext:UBLExtensions>
# <ext:UBLExtension>
# <ext:ExtensionContent>
# <extadd:ExtensionContent>
# <cacadd:ExtraParameters>
# <cbcadd:extra name="Res.Dian">Res. DIAN 18762009697450 fecha 15-08-18 Aut. Desde FCTL-1 hasta FCTL-1000000</cbcadd:extra>
# <cbcadd:extra name="Sede">CENTRAL; Cra 20 # 83 - 20  Piso 8 | Edificio Point 83 | Bog; Cundinamarca/ Colombia; 7442222</cbcadd:extra>
# <cbcadd:extra name="Tipo Factura">Counter</cbcadd:extra>
# <cbcadd:extra name="Consecutivo">Desde FCTL-1 hasta FCTL-1000000</cbcadd:extra>
# </cacadd:ExtraParameters>
# </extadd:ExtensionContent>
# </ext:ExtensionContent>
# </ext:UBLExtension>
# <ext:UBLExtension>
# <ext:ExtensionContent>
# <sts:DianExtensions>
# <sts:InvoiceControl>
# <sts:InvoiceAuthorization>18762009697450</sts:InvoiceAuthorization>
# <sts:AuthorizationPeriod>
# <cbc:StartDate>2018-08-15</cbc:StartDate>
# <cbc:EndDate>2019-08-15</cbc:EndDate>
# </sts:AuthorizationPeriod>
# <sts:AuthorizedInvoices>
# <sts:Prefix>FCTL</sts:Prefix>
# <sts:From>1</sts:From>
# <sts:To>1000000</sts:To>
# </sts:AuthorizedInvoices>
# </sts:InvoiceControl>
# <sts:InvoiceSource>
# <cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.0">CO</cbc:IdentificationCode>
# </sts:InvoiceSource>
# <sts:SoftwareProvider>
# <sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">900984424</sts:ProviderID>
# <sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">0feb477b-f3c6-4d69-b6c8-862240ffd606</sts:SoftwareID>
# </sts:SoftwareProvider>
# <sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)">633ddd36611ef22f19f9dd30cf363462dad13322cea4a3433db9cfd62a9cbd5966978562bf4a92f890df9ff35416f9cc</sts:SoftwareSecurityCode>
# </sts:DianExtensions>
# </ext:ExtensionContent>
# </ext:UBLExtension>
# <ext:UBLExtension>
# <ext:ExtensionContent>
# <ds:Signature Id="xmldsig-a719a2ae-be90-42b5-8f02-a7516545aed3-Signature" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
# <ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
# <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
# <ds:Reference Id="xmldsig-ref0" URI="">
# <ds:Transforms>
# <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
# </ds:Transforms>
# <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
# <ds:DigestValue>dY6y9/fNMCKo4+vhbQkLZjeNKRVsEvrKmWLLpjh58Hw=</ds:DigestValue></ds:Reference>
# <ds:Reference URI="#xmldsig-a719a2ae-be90-42b5-8f02-a7516545aed3-KeyInfo">
# <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
# <ds:DigestValue>nB7eUtCb2eIEddNmhH4uBV5aTGVz13+eb5nrqehURNk=</ds:DigestValue>
# </ds:Reference>
# <ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-a719a2ae-be90-42b5-8f02-a7516545aed3-SignedProperties">
# <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
# <ds:DigestValue>ncu1LvztCMbm3tFvBirpq5tGcNAtq31LbHMPzh4qItc=</ds:DigestValue>
# </ds:Reference>
# </ds:SignedInfo>
# <ds:SignatureValue Id="xmldsig-a719a2ae-be90-42b5-8f02-a7516545aed3-SignatureValue">lrQ/kqlEHEPEtWacLXIkWm+Zv5+CdTA2zfx8iBrAI3tUOCtFeIeAYg+8EEeQpCNVNnfsb/0wSjn5on6kfpu7a1YdzfwStMM/Y1s+UjYnpKvgkM9B5tXpH5Od2uE+PCmOJKGtnUYmTzFbKX26YVbBm7hfh7Dc8K37baJ4igM/V+QIA0XAaCosvkMRNaXseAk3gwLHqxA+dCLRf+LekirNahiWqTsn+i7yd5vEdxJLbv4t5fGvST4VUk891OOjllCCundISLVcAyJFwp4guR2/Ej0qiDgKPRPIgYelkxT+AFJyv0yMwRu+susu7CuMDVDbT8cIRzPViEyfXsa86kxGxA==</ds:SignatureValue>
# <ds:KeyInfo Id="xmldsig-a719a2ae-be90-42b5-8f02-a7516545aed3-KeyInfo">
# <ds:X509Data>
# <ds:X509Certificate>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</ds:X509Certificate>
# </ds:X509Data>
# </ds:KeyInfo>
# <ds:Object>
# <xades:QualifyingProperties Id="xmldsig-a719a2ae-be90-42b5-8f02-a7516545aed3-QualifyingProperties" Target="#xmldsig-a719a2ae-be90-42b5-8f02-a7516545aed3-Signature" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#">
# <xades:SignedProperties Id="xmldsig-a719a2ae-be90-42b5-8f02-a7516545aed3-SignedProperties">
# <xades:SignedSignatureProperties>
# <xades:SigningTime>2018-09-04T07:27:12-05:00</xades:SigningTime>
# <xades:SigningCertificate>
# <xades:Cert>
# <xades:CertDigest>
# <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
# <ds:DigestValue>QeLORmcqF0sEEGREp5FoSN8NQprE3lr/TNha9Fxaa00=</ds:DigestValue>
# </xades:CertDigest>
# <xades:IssuerSerial>
# <ds:X509IssuerName>CN=AC SUB CERTICAMARA, O=CERTICAMARA S.A, OU=NIT 830084433-7, C=CO, ST=DISTRITO CAPITAL, L=BOGOTA, STREET=www.certicamara.com</ds:X509IssuerName>
# <ds:X509SerialNumber>104274576352860286792940902669031852522</ds:X509SerialNumber>
# </xades:IssuerSerial>
# </xades:Cert>
# </xades:SigningCertificate>
# <xades:SignaturePolicyIdentifier>
# <xades:SignaturePolicyId>
# <xades:SigPolicyId>
# <xades:Identifier>https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf</xades:Identifier>
# <xades:Description>Politica de firma para facturas electronicas de la Republica de Colombia</xades:Description>
# </xades:SigPolicyId>
# <xades:SigPolicyHash>
# <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
# <ds:DigestValue>dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y=</ds:DigestValue>
# </xades:SigPolicyHash>
# </xades:SignaturePolicyId>
# </xades:SignaturePolicyIdentifier>
# <xades:SignerRole>
# <xades:ClaimedRoles>
# <xades:ClaimedRole>third party</xades:ClaimedRole>
# </xades:ClaimedRoles>
# </xades:SignerRole>
# </xades:SignedSignatureProperties>
# </xades:SignedProperties>
# </xades:QualifyingProperties>
# </ds:Object>
# </ds:Signature>
# </ext:ExtensionContent>
# </ext:UBLExtension>
# </ext:UBLExtensions>
# <cbc:UBLVersionID>UBL 2.0</cbc:UBLVersionID>
# <cbc:ProfileID>DIAN 1.0</cbc:ProfileID>
# <cbc:ID>FCTL15240</cbc:ID>
# <cbc:UUID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeName="CUFE">e03115e94662d414ee5ea7742646863c1dd4e34f</cbc:UUID>
# <cbc:IssueDate>2018-09-04</cbc:IssueDate>
# <cbc:IssueTime>00:27:40</cbc:IssueTime>
# <cbc:InvoiceTypeCode listAgencyID="195" listAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" listSchemeURI="http://www.dian.gov.co/contratos/facturaelectronica/v1/InvoiceType" name="factura de venta">1</cbc:InvoiceTypeCode>
# <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
# <fe:AccountingSupplierParty>
# <cbc:AdditionalAccountID>1</cbc:AdditionalAccountID>
# <fe:Party>
# <cac:PartyIdentification>
# <cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeName="31">830033206</cbc:ID>
# </cac:PartyIdentification>
# <cac:PartyName>
# <cbc:Name>BodyTech</cbc:Name>
# </cac:PartyName>
# <fe:PhysicalLocation>
# <fe:Address>
# <cbc:Department>Cundinamarca</cbc:Department>
# <cbc:CitySubdivisionName>Bogota</cbc:CitySubdivisionName>
# <cbc:CityName>Bogota</cbc:CityName>
# <cac:AddressLine>
# <cbc:Line>Carrera 20 N 82 - 20</cbc:Line>
# </cac:AddressLine>
# <cac:Country>
# <cbc:IdentificationCode>CO</cbc:IdentificationCode>
# </cac:Country>
# </fe:Address>
# </fe:PhysicalLocation>
# <fe:PartyTaxScheme>
# <cbc:TaxLevelCode>2</cbc:TaxLevelCode>
# <cac:TaxScheme/>
# </fe:PartyTaxScheme>
# <fe:PartyLegalEntity>
# <cbc:RegistrationName>Inversiones en Recreacion deporte y Salud SA</cbc:RegistrationName>
# </fe:PartyLegalEntity>
# </fe:Party>
# </fe:AccountingSupplierParty>
# <fe:AccountingCustomerParty>
# <cbc:AdditionalAccountID>1</cbc:AdditionalAccountID>
# <fe:Party>
# <cac:PartyIdentification>
# <cbc:ID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)" schemeID="13">1113306707</cbc:ID>
# </cac:PartyIdentification>
# <fe:PhysicalLocation>
# <fe:Address>
# <cbc:Department>ANTIOQUIA</cbc:Department>
# <cbc:CitySubdivisionName>ARMENIA</cbc:CitySubdivisionName>
# <cbc:CityName>ARMENIA</cbc:CityName>
# <cac:AddressLine>
# <cbc:Line>CENTRO</cbc:Line>
# </cac:AddressLine>
# <cac:Country>
# <cbc:IdentificationCode>CO</cbc:IdentificationCode>
# </cac:Country>
# </fe:Address>
# </fe:PhysicalLocation>
# <fe:PartyTaxScheme>
# <cbc:TaxLevelCode>0</cbc:TaxLevelCode>
# <cac:TaxScheme/>
# </fe:PartyTaxScheme>
# <fe:PartyLegalEntity>
# <cbc:RegistrationName>JOHN SEBASTIAN SALCEDO SALCEDO</cbc:RegistrationName>
# </fe:PartyLegalEntity>
# <cac:Contact>
# <cbc:Telephone/>
# <cbc:ElectronicMail>sebastian80_23@hotmail.com</cbc:ElectronicMail>
# </cac:Contact>
# </fe:Party>
# </fe:AccountingCustomerParty>
# <fe:TaxTotal>
# <cbc:TaxAmount currencyID="COP">0.00</cbc:TaxAmount>
# <cbc:TaxEvidenceIndicator>false</cbc:TaxEvidenceIndicator>
# <fe:TaxSubtotal>
# <cbc:TaxableAmount currencyID="COP">94900.00</cbc:TaxableAmount>
# <cbc:TaxAmount currencyID="COP">0.00</cbc:TaxAmount>
# <cbc:Percent>0.00</cbc:Percent>
# <cac:TaxCategory>
# <cac:TaxScheme>
# <cbc:ID>01</cbc:ID>
# </cac:TaxScheme>
# </cac:TaxCategory>
# </fe:TaxSubtotal>
# </fe:TaxTotal>
# <fe:LegalMonetaryTotal>
# <cbc:LineExtensionAmount currencyID="COP">94900.0000</cbc:LineExtensionAmount>
# <cbc:TaxExclusiveAmount currencyID="COP">0.0000</cbc:TaxExclusiveAmount>
# <cbc:AllowanceTotalAmount currencyID="COP">0.0000</cbc:AllowanceTotalAmount>
# <cbc:PayableAmount currencyID="COP">94900.0000</cbc:PayableAmount>
# </fe:LegalMonetaryTotal>
# <fe:InvoiceLine>
# <cbc:ID>1</cbc:ID>
# <cbc:InvoicedQuantity>1.0000</cbc:InvoicedQuantity>
# <cbc:LineExtensionAmount currencyID="COP">94900.0000</cbc:LineExtensionAmount>
# <cac:AllowanceCharge>
# <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
# <cbc:Amount currencyID="COP">0.0000</cbc:Amount>
# </cac:AllowanceCharge>
# <cac:TaxTotal>
# <cbc:TaxAmount currencyID="COP">0.00</cbc:TaxAmount>
# <cac:TaxSubtotal>
# <cbc:TaxAmount currencyID="COP">0.00</cbc:TaxAmount>
# <cbc:Percent>0.00</cbc:Percent>
# <cac:TaxCategory>
# <cac:TaxScheme>
# <cbc:ID>01</cbc:ID>
# <cbc:Name>IVA</cbc:Name>
# </cac:TaxScheme>
# </cac:TaxCategory>
# </cac:TaxSubtotal>
# </cac:TaxTotal>
# <fe:Item>
# <cbc:Description>Cuota Elite Classic (01/09/2018-30/09/2018); (7519303) JOHN SEBASTIAN SALCEDO SALCEDO</cbc:Description>
# <cac:SellersItemIdentification>
# <cbc:ID/>
# </cac:SellersItemIdentification>
# </fe:Item>
# <fe:Price>
# <cbc:PriceAmount currencyID="COP">94900.0000</cbc:PriceAmount>
# </fe:Price>
# </fe:InvoiceLine>
# </fe:Invoice>"""

#         xml_otro = xml_otro.replace('\n','')
#         xml_otro = etree.tostring(etree.fromstring(xml_otro), method="c14n")
#         print '\n\n\n\n'
#         print 'xml_otro: ', xml_otro

    # def signmessage(self, texto, key):
    #     key = crypto.load_privatekey(type_, key)
    #     signature = crypto.sign(key, texto, 'sha1')
    #     text = base64.b64encode(signature).decode()
    #     return textwrap.fill( text, 64)
            #print 'X509', crypto.X509
        #print 'get_serial_number',  get_serial_number(key)
        # #key = crypto.load_privatekey(type_,key.encode('ascii'))
        #key = crypto.load_privatekey(type_, key)
        #         signed_info_c14n = etree.tostring(signed_info,method="c14n",exclusive=False,with_comments=False,inclusive_ns_prefixes=None)
        # if type in ['doc','recep']:
        #     att = 'xmlns="http://www.w3.org/2000/09/xmldsig#"'
        # else:
        #     att = 'xmlns="http://www.w3.org/2000/09/xmldsig#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        # #@TODO Find better way to add xmlns:xsi attrib
        # signed_info_c14n = signed_info_c14n.decode().replace("<SignedInfo>", "<SignedInfo %s>" % att )


    @api.model    
    def _verificacion_manual_xml(self):
        import chilkat

        dsig = chilkat.CkXmlDSig()
        success = dsig.LoadSignature("""<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5">
<ds:SignedInfo xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:fe="http://www.dian.gov.co/contratos/facturaelectronica/v1" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"></ds:CanonicalizationMethod><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"></ds:SignatureMethod><ds:Reference Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-ref0" URI=""><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"></ds:Transform></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"></ds:DigestMethod><ds:DigestValue>csFEX5usNid+8mB/OFEfSy1aDWbt5QzpceAvSjpp+Fw=</ds:DigestValue></ds:Reference><ds:Reference URI="#xmldsig-87d128b5-aa31-4f0b-8e45-3d9cfa0eec26-keyinfo"><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"></ds:DigestMethod><ds:DigestValue>KBpAnJq4YNHNPwW2oSpmIHikXuax/uGGz7YFEht0CMg=</ds:DigestValue></ds:Reference><ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-signedprops"><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"></ds:DigestMethod><ds:DigestValue>RtqnjEoA5nHNRnbItZ1sx6i2Q0OJgbJWI/HKMp8noz4=</ds:DigestValue></ds:Reference></ds:SignedInfo>
<ds:SignatureValue Id="xmldsig-88fbfc45-3be2-4c4a-83ac-0796e1bad4c5-sigvalue">bc8D1qdfKrdfq0jjtnxxh7a+TAqEY8q8cmiXdPHZfs2txSTmltAlDPppBVPe4iB88yuBcFn0ZSYLXWHB0OhHszfQaaeZz1Q3fmpgDxCfVYK1RKT525VY5BgeQtTUrkWbHAVxgy6suJYuhOPj6GtREH0nUdoNMyOZ+T9b6ARSwvuuSGEUToJiB30oP8JgGRJH8oVXpaZ3MU+CJLMlLxFX2sfLYEQ2QLiIdPriqbGeJ/4QVm0RtmI7a7qmyVu/XWPZZ90UQFJkO55BxqFaCYmAXtpchEa925VItgF7gOzE/ujYp4dvWSsOWH32a7tbhKg5DHv5M4lmnV+/amMu3Rk4Yg==</ds:SignatureValue>""")

        numSignatures = dsig.get_NumSignatures()
        i = 0
        while i < numSignatures :
            dsig.put_Selector(i)

            bVerifyRefDigests = True
            bSignatureVerified = dsig.VerifySignature(bVerifyRefDigests)
            if (bSignatureVerified):
                print("Signature " + str(i + 1) + "verified")
            else:
                print("Signature " + str(i + 1) + "invalid")

                #  Check each of the reference digests separately..
                numRefDigests = dsig.get_NumReferences()
                j = 0
                while j < numRefDigests :
                    bDigestVerified = dsig.VerifyReferenceDigest(j)
                    print("reference digest " + str(j + 1) + " verified = " + str(bDigestVerified))
                    j = j + 1

            i = i + 1