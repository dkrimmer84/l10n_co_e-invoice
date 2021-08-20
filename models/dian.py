# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import Warning, UserError, ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import *
from pytz import timezone

import logging

_logger = logging.getLogger(__name__)

try:
    from lxml import etree
except:
    _logger.warning("Cannot import  etree *************************************")

from openerp.tools.translate import _

try:
    import pyqrcode
except ImportError:
    _logger.warning('Cannot import pyqrcode library ***************************')

try:
    import png
except ImportError:
    _logger.warning('Cannot import png library ********************************')

try:
    import hashlib
except ImportError:
    _logger.warning('Cannot import hashlib library ****************************')

try:
    import base64
except ImportError:
    _logger.warning('Cannot import base64 library *****************************')

try:
    import textwrap
except:
    _logger.warning("no se ha cargado textwrap ********************************")

try:
    import gzip
except:
    _logger.warning("no se ha cargado gzip ***********************")

import zipfile

try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    import OpenSSL
    from OpenSSL import crypto
    type_ = crypto.FILETYPE_PEM
except:
    _logger.warning('Cannot import OpenSSL library')

from random import randint

try:
    import requests 
except:    
    _logger.warning("no se ha cargado requests")
 
try:
    import xmltodict
except ImportError:
    _logger.warning('Cannot import xmltodict library')

try:
    import uuid
except ImportError:
    _logger.warning('Cannot import uuid library')

try:
    import re
except ImportError:
    _logger.warning('Cannot import re library')
         
server_url = {
    'HABILITACION':'https://facturaelectronica.dian.gov.co/habilitacion/B2BIntegrationEngine/FacturaElectronica/facturaElectronica.wsdl',
    'PRODUCCION':'https://facturaelectronica.dian.gov.co/operacion/B2BIntegrationEngine/FacturaElectronica/facturaElectronica.wsdl',
    'HABILITACION_CONSULTA':'https://facturaelectronica.dian.gov.co/habilitacion/B2BIntegrationEngine/FacturaElectronica/consultaDocumentos.wsdl',
    'PRODUCCION_CONSULTA':'https://facturaelectronica.dian.gov.co/operacion/B2BIntegrationEngine/FacturaElectronica/consultaDocumentos.wsdl',
    'PRODUCCION_VP':'https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?wsdl',
    #'PRODUCCION_VP':'https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl',                      
    'HABILITACION_VP':'https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl'
}


tipo_ambiente = {
    'PRODUCCION':'1',
    #'PRODUCCION':'2',
    'PRUEBA':'2',
    #'PRUEBA':'1'
}

tributes = {
   '01':'IVA', '02':'IC', '03':'ICA', '04':'INC', '05':'ReteIVA', '06':'ReteFuente', '07':'ReteICA', 
   '08':'ReteCREE', '20':'FtoHorticultura', '21':'Timbre', '22':'Bolsas', '23':'INCarbono', '24':'INCombustibles',
   '25':'Sobretasa Combustibles', '26':'Sordicom', 'ZY':'No causa', 'ZZ':'Nombre de la figura tributaria'
}

import os

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
                            string="Respuesta de consulta",
                            readonly=True)
    dian_code = fields.Char(string='Código DIAN', readonly=True)
    xml_document = fields.Text(string='Contenido XML del documento', readonly=True)
    xml_document_contingency = fields.Text(string='Contenido XML del documento de contigencia', readonly=True)
    xml_file_name = fields.Char(string='Nombre archivo xml', readonly=True)
    zip_file_name = fields.Char(string='Nombre archivo zip', readonly=True)
    date_request_dian = fields.Datetime(string="Fecha consulta DIAN", readonly=True)
    cufe = fields.Char(string='CUFE', readonly=True)
    QR_code = fields.Binary(string='Código QR', readonly=True)
    date_email_send = fields.Datetime(string="Fecha envío email", readonly=True)
    date_email_acknowledgment = fields.Datetime(string="Fecha acuse email", readonly=True)
    response_message_dian = fields.Text(string="Respuesta DIAN", readonly=True)
    last_shipping = fields.Boolean(string="Ultimo envío", default=True)
    customer_name = fields.Char(string="Cliente", readonly=True, related='document_id.partner_id.name')
    date_document = fields.Date(string="Fecha documento", readonly=True, related='document_id.date_invoice')
    customer_email = fields.Char(string="Email cliente", readonly=True, related='document_id.partner_id.email')
    document_type = fields.Selection([('f','Factura'), ('c','Nota/Credito'), ('d','Nota/Debito')], string="Tipo de documento", readonly=True)
    resend = fields.Boolean(string="Autorizar reenvio?", default=False)
    email_response = fields.Selection([('accepted','ACEPTADA'),('rejected','RECHAZADA'),('pending','PENDIENTE')], string='Decisión del cliente', required=True, default='pending', readonly=True)
    email_reject_reason = fields.Char(string='Motivo del rechazo', readonly=True)
    ZipKey = fields.Char(string='Identificador del docuemnto enviado', readonly=True)
    xml_response_dian = fields.Text(string='Contenido XML de la respuesta DIAN', readonly=True)
    xml_send_query_dian = fields.Text(string='Contenido XML de envío de consulta de documento DIAN', readonly=True)
    xml_response_contingency_dian = fields.Text(string='Mensaje de respuesta DIAN al envío de la contigencia', readonly=True)
    state_contingency = fields.Selection([('por_notificar','por_notificar'),
                            ('exitosa', 'Exitosa'), 
                            ('rechazada', 'Rechazada')],
                            string="Estatus de contingencia",
                            readonly=True,
                            default='por_notificar',
                            required=True)
    contingency_3 = fields.Boolean(string='Contingencia tipo 3', related='document_id.contingency_3')
    contingency_4 = fields.Boolean(string='Contingencia tipo 4', related='document_id.contingency_4')
    count_error_DIAN = fields.Integer(string="contador de intentos fallidos por problemas de la DIAN", default=0)
    date_error_DIAN_1 = fields.Datetime(string='Fecha del 1er. mensaje de error DIAN')
    message_error_DIAN_1 = fields.Text(string='Mensaje del 1er. error de respuesta DIAN')
    date_error_DIAN_2 = fields.Datetime(string='Fecha del 2do. mensaje de error DIAN')
    message_error_DIAN_2 = fields.Text(string='Mensaje del 2do. error de respuesta DIAN')
    date_error_DIAN_3 = fields.Datetime(string='Fecha del 3er. mensaje de error DIAN')
    message_error_DIAN_3 = fields.Text(string='Mensaje del 3er. error de respuesta DIAN')

       
    @api.model
    def _get_resolution_dian(self, data_header_doc):
        _logger.info('_get_resolution_dian|start')
        #rec_active_resolution = self.env['ir.sequence.dian_resolution'].search([('resolution_number', '=', data_header_doc.resolution_number)])
        rec_active_resolution = data_header_doc.journal_id.sequence_id.dian_resolution_ids.filtered(lambda r: r.resolution_number == data_header_doc.resolution_number)
        dict_resolution_dian = {}
        if rec_active_resolution:
            rec_dian_sequence = self.env['ir.sequence'].search([('id', '=', rec_active_resolution.sequence_id.id)])
            dict_resolution_dian['Prefix'] = rec_dian_sequence.prefix                               # Prefijo de número de factura
            dict_resolution_dian['InvoiceAuthorization'] = rec_active_resolution.resolution_number  # Número de resolución
            dict_resolution_dian['StartDate'] = rec_active_resolution.date_from                     # Fecha desde resolución
            dict_resolution_dian['EndDate'] = rec_active_resolution.date_to                         # Fecha hasta resolución
            dict_resolution_dian['From'] = rec_active_resolution.number_from                        # Desde la secuencia
            dict_resolution_dian['To'] = rec_active_resolution.number_to                            # Hasta la secuencia
            dict_resolution_dian['TechnicalKey'] = rec_active_resolution.technical_key              # Clave técnica de la resolución de rango
            dict_resolution_dian['InvoiceID'] = data_header_doc.number                              # Codigo del documento
            #13FEB dict_resolution_dian['ContingencyID'] = data_header_doc.contingency_invoice_number 
            dict_resolution_dian['ContingencyID'] = data_header_doc.number     # Número de fcatura de contingencia
        else:
            raise ValidationError("El número de resolución DIAN asociada a la factura no existe")
        return dict_resolution_dian


    @api.model
    def request_validating_dian(self, document_id):
        _logger.info('request_validating_dian|start')
        _logger.info('request_validating_dian|document_id|' + str(document_id))
        user = self.env['res.users'].sudo().search([('id', '=', self.env.uid)])
        company = self.env['res.company'].sudo().search([('id', '=', user.company_id.id)])
        dian_document = self.env['dian.document'].search([('id', '=', document_id)])
        data_header_doc = self.env['account.invoice'].search([('id', '=', dian_document.document_id.id)])
        dian_constants = self._get_dian_constants(data_header_doc)
        trackId = dian_document.ZipKey
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self._generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        template_GetStatus_xml = self._template_GetStatus_xml()
        data_xml_send = self._generate_GetStatus_send_xml(template_GetStatus_xml, identifier, Created, Expires, 
            dian_constants['Certificate'], identifierSecurityToken, identifierTo, trackId)
        
        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_send = etree.tostring(etree.XML(data_xml_send, parser=parser))
        data_xml_send = data_xml_send.decode()
        #   Generar DigestValue Elemento to y lo reemplaza en el xml
        ElementTO = etree.fromstring(data_xml_send)
        ElementTO = etree.tostring(ElementTO[0])
        ElementTO = etree.fromstring(ElementTO)
        ElementTO = etree.tostring(ElementTO[2])
        DigestValueTO = self._generate_digestvalue_to(ElementTO)
        data_xml_send = data_xml_send.replace('<ds:DigestValue/>','<ds:DigestValue>%s</ds:DigestValue>' % DigestValueTO)
        #   Generar firma para el header de envío con el Signedinfo
        Signedinfo = etree.fromstring(data_xml_send)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[2])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        Signedinfo = Signedinfo.replace('<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">',
                                        '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia" xmlns:wsa="http://www.w3.org/2005/08/addressing">')
        SignatureValue = self._generate_SignatureValue_GetStatus(dian_constants['document_repository'], dian_constants['CertificateKey'], Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
        data_xml_send = data_xml_send.replace('<ds:SignatureValue/>','<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)
        #   Contruye XML de envío de petición
        headers = {'content-type': 'application/soap+xml'}
        URL_WEBService_DIAN = server_url['PRODUCCION_VP'] if company.production else server_url['HABILITACION_VP']
        try:
            response = requests.post(URL_WEBService_DIAN,data=data_xml_send,headers=headers)
        except:
            raise ValidationError('No existe comunicación con la DIAN para el servicio de recepción de Facturas Electrónicas. Por favor, revise su red o el acceso a internet.')
        #   Respuesta de petición
        _logger.info('request_validating_dian|response.status_code|' + str(response.status_code))
        if response.status_code != 200: # Respuesta de envío no exitosa
            if response.status_code == 500:
                raise ValidationError('Error 500 = Error de servidor interno.')
            elif response.status_code == 503:
                raise ValidationError('Error 503 = Servicio no disponible.')
            elif response.status_code == 507:
                raise ValidationError('Error 507 = Espacio insuficiente.')
            elif response.status_code == 508:
                raise ValidationError('Error 508 = Ciclo detectado.')
            else:
                raise ValidationError('Se ha producido un error de comunicación con la DIAN.')
        response_dict = xmltodict.parse(response.content)
        _logger.info('request_validating_dian|response_dict|' + str(response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse']['b:StatusCode']))
        if response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse']['b:StatusCode'] == '00':
            _logger.info('request_validating_dian|response_dict|production|')
            data_header_doc.write({'diancode_id' : dian_document.id})
            dian_document.response_message_dian += '- Respuesta consulta estado del documento: Procesado correctamente \n'
            dian_document.write({'state' : 'exitoso', 'resend' : False})
            # Envío de correo
            if dian_document.contingency_4 == False:
                if self.enviar_email(dian_document.xml_document, dian_document.document_id.id, dian_document.xml_file_name, dian_constants['document_repository']):
                    dian_document.date_email_send = fields.Datetime.now()
        else:
            # Test environment
            _logger.info('request_validating_dian|response_dict|dev|')          
            data_header_doc.write({'diancode_id' : dian_document.id})
            if self.enviar_email(dian_document.xml_document, dian_document.document_id.id, dian_document.xml_file_name, dian_constants['document_repository']):
                _logger.info('request_validating_dian|response_dict|dev|date_email_send|call')
                dian_document.date_email_send = fields.Datetime.now()

            if response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse']['b:StatusCode'] == '90':                
                dian_document.response_message_dian += '- Respuesta consulta estado del documento: TrackId no encontrado'
                dian_document.write({'state' : 'por_validar', 'resend' : False})
            elif response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse']['b:StatusCode'] == '99':
                dian_document.response_message_dian += '- Respuesta consulta estado del documento: Validaciones contiene errores en campos mandatorios'
                dian_document.write({'state' : 'rechazado', 'resend' : True})
            elif response_dict['s:Envelope']['s:Body']['GetStatusZipResponse']['GetStatusZipResult']['b:DianResponse']['b:StatusCode'] == '66':
                dian_document.response_message_dian += '- Respuesta consulta estado del documento: NSU no encontrado'
                dian_document.write({'state' : 'por_validar', 'resend' : False})
            dian_document.xml_response_dian = response.content
            dian_document.xml_send_query_dian = data_xml_send
        return True


    @api.model
    def exist_dian(self, document_id):
        _logger.info('exist_dian|start')
        dic_result_verify_status  = {}
        user = self.env['res.users'].search([('id', '=', self.env.uid)])
        company = self.env['res.company'].search([('id', '=', user.company_id.id)])
    
        dian_document = self.env['dian.document'].search([('id', '=', document_id)])
        data_header_doc = self.env['account.invoice'].search([('id', '=', dian_document.document_id.id)])
        dian_constants = self._get_dian_constants(data_header_doc)
        trackId = dian_document.ZipKey
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self._generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']

        if company.production:  
            template_GetStatus_xml = self._template_GetStatusExist_xml()
        else:
            template_GetStatus_xml = self._template_GetStatusExistTest_xml()

        data_xml_send = self._generate_GetStatus_send_xml(template_GetStatus_xml, identifier, Created, Expires, 
            dian_constants['Certificate'], identifierSecurityToken, identifierTo, trackId)
        
        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_send = etree.tostring(etree.XML(data_xml_send, parser=parser))
        data_xml_send = data_xml_send.decode()
        #   Generar DigestValue Elemento to y lo reemplaza en el xml
        ElementTO = etree.fromstring(data_xml_send)
        ElementTO = etree.tostring(ElementTO[0])
        ElementTO = etree.fromstring(ElementTO)
        ElementTO = etree.tostring(ElementTO[2])
        DigestValueTO = self._generate_digestvalue_to(ElementTO)
        data_xml_send = data_xml_send.replace('<ds:DigestValue/>','<ds:DigestValue>%s</ds:DigestValue>' % DigestValueTO)
        #   Generar firma para el header de envío con el Signedinfo
        Signedinfo = etree.fromstring(data_xml_send)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[2])
        Signedinfo = etree.fromstring(Signedinfo)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        Signedinfo = Signedinfo.replace('<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">',
                                        '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia" xmlns:wsa="http://www.w3.org/2005/08/addressing">')
        SignatureValue = self._generate_SignatureValue_GetStatus(dian_constants['document_repository'], dian_constants['CertificateKey'], Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
        data_xml_send = data_xml_send.replace('<ds:SignatureValue/>','<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)
        #   Contruye XML de envío de petición
        headers = {'content-type': 'application/soap+xml'}
        URL_WEBService_DIAN = server_url['PRODUCCION_VP'] if company.production else server_url['HABILITACION_VP']
        try:
            response = requests.post(URL_WEBService_DIAN,data=data_xml_send,headers=headers)
        except:
            raise ValidationError('No existe comunicación con la DIAN para el servicio de recepción de Facturas Electrónicas. Por favor, revise su red o el acceso a internet.')
        #   Respuesta de petición
        _logger.info('exist_dian|response.status_code|' + str(response.status_code))
        if response.status_code != 200: # Respuesta de envío no exitosa
            if response.status_code == 500:
                raise ValidationError('Error 500 = Error de servidor interno.')
            elif response.status_code == 503:
                raise ValidationError('Error 503 = Servicio no disponible.')
            elif response.status_code == 507:
                raise ValidationError('Error 507 = Espacio insuficiente.')
            elif response.status_code == 508:
                raise ValidationError('Error 508 = Ciclo detectado.')
            else:
                raise ValidationError('Se ha producido un error de comunicación con la DIAN.')
        response_dict = xmltodict.parse(response.content)

        dic_result_verify_status['result_verify_status'] = False
        if response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusCode'] == '00':
            _logger.info('exist_dian|response_dict|StatusCode|' + str(response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusCode']))
            dic_result_verify_status['result_verify_status'] = True

        dic_result_verify_status['response_message_dian'] = response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusCode'] + ' '  
        dic_result_verify_status['response_message_dian'] += response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusDescription'] + '\n'
        #dic_result_verify_status['response_message_dian'] += response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:StatusMessage']
        dic_result_verify_status['ZipKey'] = response_dict['s:Envelope']['s:Body']['GetStatusResponse']['GetStatusResult']['b:XmlDocumentKey']
        return dic_result_verify_status 


    @api.model
    def send_pending_dian(self, document_id, document_type):
        _logger.info('send_pending_dian|start')
        dic_result_verify_status = self.exist_dian(self.id) 
        if dic_result_verify_status['result_verify_status'] == False:
            resultado = self._get_datetime()
            user = self.env['res.users'].search([('id', '=', self.env.uid)])
            company = self.env['res.company'].sudo().search([('id', '=', user.company_id.id)])
            data_lines_xml = ''
            data_credit_lines_xml = ''
            data_xml_signature = ''
            parser = etree.XMLParser(remove_blank_text=True)
            template_basic_data_fe_xml = self._template_basic_data_fe_xml()
            template_basic_data_nc_xml = self._template_basic_data_nc_xml()
            template_basic_data_nd_xml = self._template_basic_data_nd_xml()
            template_basic_data_contingencia_xml = self._template_basic_data_contingencia_xml()
            template_tax_data_xml = self._template_tax_data_xml()
            template_line_data_xml = self._template_line_data_xml()
            template_credit_line_data_xml = self._template_credit_line_data_xml()
            template_debit_line_data_xml = self._template_debit_line_data_xml()
            template_signature_data_xml = self._template_signature_data_xml()
            template_send_data_xml = self._template_send_data_xml()
            # Se obtienen los documento a enviar
            if document_type == 'f':
                by_validate_invoices = self.env['dian.document'].search([('id', '=', document_id),('document_type', '=', document_type)])
                if by_validate_invoices:
                    docs_send_dian = by_validate_invoices
                else:
                    raise ValidationError('La factura no está en proceso de envío a la DIAN. Contacte al administrador del sistema')
            if document_type == 'c':
                by_validate_credit_notes = self.env['dian.document'].search([('id', '=', document_id),('document_type', '=', document_type)])
                cn_with_validated_invoices_ids = []
                for by_validate_cn in by_validate_credit_notes:
                    invoice_validated = self.env['account.invoice'].search([('move_name', '=', by_validate_cn.document_id.origin),('type', '=', 'out_invoice'),('state_dian_document', '=', 'exitoso')])
                    if invoice_validated:
                        cn_with_validated_invoices_ids.append(by_validate_cn.id)
                    else:
                        raise ValidationError('La factura a la que se le va a aplicar la nota de crédito, no ha sido enviada o aceptada por la DIAN')
                by_validate_credit_notes_autorized = self.env['dian.document'].browse(cn_with_validated_invoices_ids)
                docs_send_dian = by_validate_credit_notes_autorized
            if document_type == 'd':
                by_validate_debit_notes = self.env['dian.document'].search([('id', '=', document_id),('document_type', '=', document_type)])
                cn_with_validated_invoices_ids = []
                for by_validate_cn in by_validate_debit_notes:
                    invoice_validated = self.env['account.invoice'].search([('move_name', '=', by_validate_cn.document_id.origin),('type', '=', 'out_invoice'),('state_dian_document', '=', 'exitoso')])
                    if invoice_validated:
                        cn_with_validated_invoices_ids.append(by_validate_cn.id)
                    else:
                        raise ValidationError('La factura a la que se le va a aplicar la nota de débito, no ha sido enviada o aceptada por la DIAN')
                by_validate_debit_notes_autorized = self.env['dian.document'].browse(cn_with_validated_invoices_ids)
                docs_send_dian = by_validate_debit_notes_autorized

            if document_type == 'contingency' and self.contingency_3:
                by_validate_invoices = self.env['dian.document'].search([('id', '=', document_id),('document_type', '=',  'f')])
                if by_validate_invoices:
                    docs_send_dian = by_validate_invoices
                else:
                    raise ValidationError('La factura no está en proceso de envío a la DIAN. Contacte al administrador del sistema')
            for doc_send_dian in docs_send_dian:
                data_header_doc = self.env['account.invoice'].search([('id', '=', doc_send_dian.document_id.id)])
                dian_constants = self._get_dian_constants(data_header_doc)
                # Se obtienen constantes del documento
                data_constants_document = self._generate_data_constants_document(data_header_doc, dian_constants, document_type, company.in_contingency_4)            
                # Construye el documento XML para la factura sin firma
                _logger.info('send_pending_dian|data_constants_document|InvoiceTypeCode|' + str(data_constants_document['InvoiceTypeCode']))
                if data_constants_document['InvoiceTypeCode'] in ('01','04'):
                    # Genera líneas de detalle de los impuestos
                    data_taxs = self._get_taxs_data(data_header_doc.id)
                    data_taxs_xml = self._generate_taxs_data_xml(template_tax_data_xml, data_taxs, data_constants_document['CurrencyID'], document_type)
                    # Genera líneas de detalle de las factura
                    data_lines_xml = self._generate_lines_data_xml(template_line_data_xml, data_header_doc.id, data_constants_document['CurrencyID'])
                    # Generar CUFE
                    ambiente = tipo_ambiente['PRODUCCION'] if company.production else tipo_ambiente['PRUEBA']
                    CUFE = self._generate_cufe(data_header_doc.id, data_constants_document['InvoiceID'], data_constants_document['IssueDateCufe'], 
                                            data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'],
                                            dian_constants['SupplierID'], data_constants_document['CustomerSchemeID'],
                                            data_constants_document['CustomerID'], data_constants_document['TechnicalKey'], data_constants_document['PayableAmount'], 
                                            data_taxs, ambiente)
                    doc_send_dian.cufe = CUFE
                    # Genera documento xml de la factura
                    template_basic_data_fe_xml = '<?xml version="1.0"?>' + template_basic_data_fe_xml
                    template_basic_data_fe_xml = etree.tostring(etree.XML(template_basic_data_fe_xml, parser=parser))
                    template_basic_data_fe_xml = template_basic_data_fe_xml.decode()
                    data_xml_document = self._generate_data_fe_document_xml(template_basic_data_fe_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature)
                    # Elimina espacios del documento xml la factura
                    data_xml_document = etree.tostring(etree.XML(data_xml_document, parser=parser))
                    data_xml_document = data_xml_document.decode()
                # Construye el documento XML para la nota de crédito sin firma
                if data_constants_document['InvoiceTypeCode'] == '91':
                    data_taxs = self._get_taxs_data(data_header_doc.id)
                    data_taxs_xml = self._generate_taxs_data_xml(template_tax_data_xml, data_taxs, data_constants_document['CurrencyID'],document_type)
                    # Detalle líneas de nota de crédito                
                    data_credit_lines_xml = self._generate_credit_lines_data_xml(template_credit_line_data_xml, data_header_doc.id, data_constants_document['CurrencyID'])
                    # Generar CUDE
                    ambiente = tipo_ambiente['PRODUCCION'] if company.production else tipo_ambiente['PRUEBA']
                    CUFE = self._generate_cude(data_header_doc.id, data_constants_document['InvoiceID'], data_constants_document['IssueDateCufe'], 
                            data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'],
                            dian_constants['SupplierID'], data_constants_document['CustomerSchemeID'],
                            data_constants_document['CustomerID'], dian_constants['PINSoftware'], data_constants_document['PayableAmount'], 
                            data_taxs, ambiente)
                    doc_send_dian.cufe = CUFE
                    # Genera documento xml de la nota de crédito
                    template_basic_data_nc_xml = '<?xml version="1.0"?>' + template_basic_data_nc_xml
                    template_basic_data_nc_xml = etree.tostring(etree.XML(template_basic_data_nc_xml, parser=parser))
                    template_basic_data_nc_xml = template_basic_data_nc_xml.decode()
                    data_xml_document = self._generate_data_nc_document_xml(template_basic_data_nc_xml, dian_constants, data_constants_document, data_credit_lines_xml, CUFE, data_taxs_xml)
                    # Elimina espacios del documento xml
                    data_xml_document = etree.tostring(etree.XML(data_xml_document, parser=parser))
                    data_xml_document = data_xml_document.decode()
                # Construye el documento XML para la nota de dédito sin firma
                if data_constants_document['InvoiceTypeCode'] == '92':
                    data_taxs = self._get_taxs_data(data_header_doc.id)
                    data_taxs_xml = self._generate_taxs_data_xml(template_tax_data_xml, data_taxs, data_constants_document['CurrencyID'],document_type)
                    # Detalle líneas de nota de crédito                
                    data_debit_lines_xml = self._generate_debit_lines_data_xml(template_debit_line_data_xml, data_header_doc.id, data_constants_document['CurrencyID'])
                    # Generar CUFE
                    ambiente = tipo_ambiente['PRODUCCION'] if company.production else tipo_ambiente['PRUEBA']
                    CUFE = self._generate_cude(data_header_doc.id, data_constants_document['InvoiceID'], data_constants_document['IssueDateCufe'], 
                            data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'],
                            dian_constants['SupplierID'], data_constants_document['CustomerSchemeID'],
                            data_constants_document['CustomerID'], dian_constants['PINSoftware'], data_constants_document['PayableAmount'], 
                            data_taxs, ambiente)
                    doc_send_dian.cufe = CUFE
                    # Genera documento xml de la nota de débiito
                    template_basic_data_nd_xml = '<?xml version="1.0"?>' + template_basic_data_nd_xml
                    template_basic_data_nd_xml = etree.tostring(etree.XML(template_basic_data_nd_xml, parser=parser))
                    template_basic_data_nd_xml = template_basic_data_nd_xml.decode()
                    data_xml_document = self._generate_data_nd_document_xml(template_basic_data_nd_xml, dian_constants, data_constants_document, data_debit_lines_xml, CUFE, data_taxs_xml)
                    # Elimina espacios del documento xml                
                    data_xml_document = etree.tostring(etree.XML(data_xml_document, parser=parser))
                    data_xml_document = data_xml_document.decode()
                # Construye el documento XML para la factura de contingencia sin firma
                if data_constants_document['InvoiceTypeCode'] == '03':
                    data_taxs = self._get_taxs_data(data_header_doc.id)
                    data_taxs_xml = self._generate_taxs_data_xml(template_tax_data_xml, data_taxs, data_constants_document['CurrencyID'],document_type)
                    # Genera líneas de detalle de las factura
                    data_lines_xml = self._generate_lines_data_xml(template_line_data_xml, data_header_doc.id, data_constants_document['CurrencyID'])
                    # Generar CUDE
                    ambiente = tipo_ambiente['PRODUCCION'] if company.production else tipo_ambiente['PRUEBA']
                    CUFE = self._generate_cude(data_header_doc.id, data_constants_document['InvoiceID'], data_constants_document['IssueDateCufe'], 
                            data_constants_document['IssueTime'], data_constants_document['LineExtensionAmount'],
                            dian_constants['SupplierID'], data_constants_document['CustomerSchemeID'],
                            data_constants_document['CustomerID'], dian_constants['PINSoftware'], data_constants_document['PayableAmount'], 
                            data_taxs, ambiente)
                    doc_send_dian.cufe = CUFE
                    # Genera documento xml de la factura
                    template_basic_data_contingencia_xml = '<?xml version="1.0"?>' + template_basic_data_contingencia_xml
                    template_basic_data_contingencia_xml = etree.tostring(etree.XML(template_basic_data_contingencia_xml, parser=parser))
                    template_basic_data_contingencia_xml = template_basic_data_contingencia_xml.decode()
                    data_xml_document = self._generate_data_contingencia_document_xml(template_basic_data_contingencia_xml, dian_constants, data_constants_document, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature)
                    # Elimina espacios del documento xml la factura
                    data_xml_document = etree.tostring(etree.XML(data_xml_document, parser=parser))
                    data_xml_document = data_xml_document.decode()
                # Genera la firma en el documento xml
                data_xml_document = data_xml_document.replace("<ext:ExtensionContent/>","<ext:ExtensionContent></ext:ExtensionContent>")
                data_xml_signature = self._generate_signature(data_xml_document, template_signature_data_xml, dian_constants, data_constants_document)
                data_xml_signature = etree.tostring(etree.XML(data_xml_signature, parser=parser))
                data_xml_signature = data_xml_signature.decode()
                # Construye el documento XML con firma
                data_xml_document = data_xml_document.replace("<ext:ExtensionContent></ext:ExtensionContent>","<ext:ExtensionContent>%s</ext:ExtensionContent>" % data_xml_signature)
                data_xml_document = '<?xml version="1.0" encoding="UTF-8"?>' + data_xml_document
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
                fileName = data_constants_document['FileNameZIP'][:-4]
                # Fecha y hora de la petición y expiración del envío del documento
                timestamp = self._generate_datetime_timestamp()
                Created = timestamp['Created']
                Expires = timestamp['Expires']
                doc_send_dian.date_document_dian = data_constants_document['IssueDateSend']
                # Id de pruebas
                testSetId = company.identificador_set_pruebas
                identifierSecurityToken = uuid.uuid4()
                identifierTo = uuid.uuid4()            
                # Preparación del envío de la factura 
                _logger.info('send_pending_dian|company.production|' + str(company.production))
                if company.production:                                     
                    #template_SendBillSyncsend_xml = self._template_SendBillSyncsend_xml()
                    template_SendBillSyncsend_xml = self._template_SendBillSyncsend_xml()
                    data_xml_send = self._generate_SendBillSync_send_xml(template_SendBillSyncsend_xml, fileName, 
                                    Document, Created, testSetId, data_constants_document['identifier'], Expires, 
                                    dian_constants['Certificate'], identifierSecurityToken, identifierTo)
                    # Por lotes
                    # template_SendBillAsyncsend_xml = self._template_SendBillAsyncsend_xml()
                    # data_xml_send = self._generate_SendBillAsync_send_xml(template_SendBillAsyncsend_xml, fileName, 
                    #                 Document, Created, testSetId, data_constants_document['identifier'], Expires, 
                    #                 dian_constants['Certificate'], identifierSecurityToken, identifierTo)
                else:
                    template_SendTestSetAsyncsend_xml = self._template_SendBillSyncTestsend_xml()
                    data_xml_send = self._generate_SendTestSetAsync_send_xml(template_SendTestSetAsyncsend_xml, fileName, 
                                    Document, Created, testSetId, data_constants_document['identifier'], Expires, 
                                    dian_constants['Certificate'], identifierSecurityToken, identifierTo)


                    # Por lotes
                    # template_SendTestSetAsyncsend_xml = self._template_SendTestSetAsyncsend_xml()
                    # data_xml_send = self._generate_SendTestSetAsync_send_xml(template_SendTestSetAsyncsend_xml, fileName, 
                    #                 Document, Created, testSetId, data_constants_document['identifier'], Expires, 
                    #                 dian_constants['Certificate'], identifierSecurityToken, identifierTo)

                parser = etree.XMLParser(remove_blank_text=True)
                data_xml_send = etree.tostring(etree.XML(data_xml_send, parser=parser))
                data_xml_send = data_xml_send.decode()
                #   Generar DigestValue Elemento to y lo reemplaza en el xml
                ElementTO = etree.fromstring(data_xml_send)
                ElementTO = etree.tostring(ElementTO[0])
                ElementTO = etree.fromstring(ElementTO)
                ElementTO = etree.tostring(ElementTO[2])
                DigestValueTO = self._generate_digestvalue_to(ElementTO)
                data_xml_send = data_xml_send.replace('<ds:DigestValue/>','<ds:DigestValue>%s</ds:DigestValue>' % DigestValueTO)
                #   Generar firma para el header de envío con el Signedinfo
                Signedinfo = etree.fromstring(data_xml_send)
                Signedinfo = etree.tostring(Signedinfo[0])
                Signedinfo = etree.fromstring(Signedinfo)
                Signedinfo = etree.tostring(Signedinfo[0])
                Signedinfo = etree.fromstring(Signedinfo)
                Signedinfo = etree.tostring(Signedinfo[2])
                Signedinfo = etree.fromstring(Signedinfo)
                Signedinfo = etree.tostring(Signedinfo[0])
                Signedinfo = Signedinfo.decode()
                Signedinfo = Signedinfo.replace('<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">',
                                                '<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia" xmlns:wsa="http://www.w3.org/2005/08/addressing">')
                SignatureValue = self._generate_SignatureValue_GetStatus(dian_constants['document_repository'], dian_constants['CertificateKey'], Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
                data_xml_send = data_xml_send.replace('<ds:SignatureValue/>','<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)
                
                #   Contruye XML de envío de petición                
                headers = {'content-type': 'application/soap+xml'}
                URL_WEBService_DIAN = server_url['PRODUCCION_VP'] if company.production else server_url['HABILITACION_VP']

                if company.in_contingency_4 == False: # Diferente a contingencia tipo 4 (Problemas tecnológicos en la DIAN)
                    _logger.info('send_pending_dian|requests.post|initiate')
                    try:
                        response = requests.post(URL_WEBService_DIAN,data=data_xml_send,headers=headers)
                    except:
                        raise ValidationError('No existe comunicación con la DIAN para el servicio de recepción de Facturas Electrónicas. Por favor, revise su red o el acceso a internet.')
                    
                    # code = 500
                    # if code != 200:
                    _logger.info('send_pending_dian|requests.post|response.status_code|' + str(response.status_code))
                    if response.status_code != 200: # Respuesta de envío no exitosa

                        # if code in (500,503,507,508):
                        #     message_error_DIAN = str(code) + ' ' + 'Prueba'

                        message_error_DIAN = str(response.status_code) + ' ' + response.content.decode()
                        if response.status_code in (500,503,507,508):
                            data_header_doc.write({'diancode_id' : doc_send_dian.id})
                            if doc_send_dian.count_error_DIAN == 0:
                                doc_send_dian.date_error_DIAN_1 = self._get_datetime()
                                doc_send_dian.message_error_DIAN_1 = message_error_DIAN
                                doc_send_dian.count_error_DIAN = 1
                            elif doc_send_dian.count_error_DIAN == 1:
                                doc_send_dian.date_error_DIAN_2 = self._get_datetime()
                                doc_send_dian.message_error_DIAN_2 = message_error_DIAN
                                doc_send_dian.count_error_DIAN = 2
                            elif doc_send_dian.count_error_DIAN == 2:
                                doc_send_dian.date_error_DIAN_3 = self._get_datetime()
                                doc_send_dian.message_error_DIAN_3 = message_error_DIAN
                                doc_send_dian.count_error_DIAN = 3
                            elif doc_send_dian.count_error_DIAN == 3:
                                company.in_contingency_4 = True
                                company.date_init_contingency_4 = self._get_datetime()
                                doc_send_dian.count_error_DIAN = 0
                                if company.in_contingency_4 == True and self.contingency_3 == False:
                                    document_type = self.document_type
                                else:
                                    document_type = self.document_type if self.contingency_3 == False else 'contingency'
                                #document_type = self.document_type if self.contingency_3 == False and  self.contingency_4 == False else 'contingency'
                                self.send_pending_dian(self.id, document_type)
                        else:
                            raise ValidationError(message_error_DIAN)
                    else:
                        # Procesa respuesta DIAN 
                        response_dict = xmltodict.parse(response.content)
                        dict_mensaje = {}
                        _logger.info('send_pending_dian|requests.post|' + str(response.status_code) + '|company.production|' + str(company.production))                        
                        if company.production:                                                        
                            _logger.info('send_pending_dian|requests.post|production')
                            dict_result_verify_status = self.exist_dian(self.id) 
                            if dict_result_verify_status['result_verify_status'] == True:
                                _logger.info('send_pending_dian|requests.post|dict_result_verify_status|result_verify_status|True')
                                return
                            _logger.info('send_pending_dian|requests.post|dict_result_verify_status|False')
                            dict_mensaje = response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:IsValid']
                            doc_send_dian.response_message_dian = ' '
                            #if response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:IsValid'] == 'true':                            
                            if response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:StatusCode'] == '00':
                                _logger.info('send_pending_dian|requests.post|dict_result_verify_status|response|StatusCode' + str(response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:StatusCode']))
                                doc_send_dian.response_message_dian = response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:StatusCode'] + ' '  
                                doc_send_dian.response_message_dian += response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:StatusDescription'] + '\n'
                                doc_send_dian.response_message_dian += response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:StatusMessage']
                                doc_send_dian.ZipKey = response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:XmlDocumentKey']
                                doc_send_dian.xml_response_dian = response.content
                                doc_send_dian.xml_send_query_dian = data_xml_send
                                doc_send_dian.write({'state' : 'exitoso', 'resend' : False})
                                if doc_send_dian.contingency_3:
                                    doc_send_dian.write({'state_contingency' : 'exitosa'})
                                data_header_doc.write({'diancode_id' : doc_send_dian.id})                        
                                # Generar código QR
                                doc_send_dian.QR_code = self.sudo()._generate_barcode(dian_constants, data_constants_document, CUFE, data_taxs)
                                # Envío de correo
                                if doc_send_dian.contingency_4 == False:
                                    if self.enviar_email(data_xml_document, doc_send_dian.document_id.id, fileName, dian_constants['document_repository']):
                                        doc_send_dian.date_email_send = fields.Datetime.now()
                            else:
                                _logger.info('send_pending_dian|requests.post|StatusCode|not00')
                                doc_send_dian.response_message_dian = response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:StatusCode'] + ' '  
                                doc_send_dian.response_message_dian += response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:StatusDescription'] + '\n'
                                doc_send_dian.response_message_dian += response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:StatusMessage']
                                doc_send_dian.ZipKey = response_dict['s:Envelope']['s:Body']['SendBillSyncResponse']['SendBillSyncResult']['b:XmlDocumentKey']
                                doc_send_dian.xml_response_dian = response.content
                                doc_send_dian.xml_send_query_dian = data_xml_send
                                doc_send_dian.write({'state' : 'rechazado', 'resend' : True})
                                if doc_send_dian.contingency_3:
                                    doc_send_dian.write({'state_contingency' : 'rechazada'})
                                data_header_doc.write({'diancode_id' : doc_send_dian.id})
                                # Generar código QR
                                doc_send_dian.QR_code = self.sudo()._generate_barcode(dian_constants, data_constants_document, CUFE, data_taxs)
                        else: # Ambiente de pruebas
                            _logger.info('send_pending_dian|requests.post|dev')
                            dict_mensaje = response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult']['b:ErrorMessageList']
                            if '@i:nil' in dict_mensaje:
                                if response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult']['b:ErrorMessageList']['@i:nil'] == 'true':
                                    doc_send_dian.response_message_dian = '- Respuesta envío: Documento enviado con éxito. Falta validar su estado \n'
                                    doc_send_dian.ZipKey = response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult']['b:ZipKey']
                                    doc_send_dian.state = 'por_validar'
                                else:
                                    doc_send_dian.response_message_dian = '- Respuesta envío: Documento enviado con éxito, pero la DIAN detectó errores \n'
                                    doc_send_dian.ZipKey = response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult']['b:ZipKey']
                                    doc_send_dian.state = 'por_notificar'
                            elif 'i:nil' in dict_mensaje:
                                if response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult']['b:ErrorMessageList']['i:nil'] == 'true':
                                    doc_send_dian.response_message_dian = '- Respuesta envío: Documento enviado con éxito. Falta validar su estado \n'
                                    doc_send_dian.ZipKey = response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult']['b:ZipKey']
                                    doc_send_dian.state = 'por_validar'
                                else:
                                    doc_send_dian.response_message_dian = '- Respuesta envío: Documento enviado con éxito, pero la DIAN detectó errores \n'
                                    doc_send_dian.ZipKey = response_dict['s:Envelope']['s:Body']['SendTestSetAsyncResponse']['SendTestSetAsyncResult']['b:ZipKey']
                                    doc_send_dian.state = 'por_notificar'
                            else:
                                raise ValidationError('Mensaje de respuesta cambió en su estructura xml')
                            # Generar código QR
                            doc_send_dian.QR_code = self.sudo()._generate_barcode(dian_constants, data_constants_document, CUFE, data_taxs)
                else: # Contigencia tipo 4
                    _logger.info('send_pending_dian|contingency_4|initiate')
                    data_header_doc.contingency_4 = True                
                    doc_send_dian.xml_document_contingency = data_xml_document
                    doc_send_dian.xml_send_query_dian = data_xml_send
                    # Generar código QR
                    doc_send_dian.QR_code = self.sudo()._generate_barcode(dian_constants, data_constants_document, CUFE, data_taxs)
                    
                    # Enviar email
                    data_header_doc.write({'diancode_id' : doc_send_dian.id})
                    if self.enviar_email(data_xml_document, doc_send_dian.document_id.id, fileName, dian_constants['document_repository']):
                        doc_send_dian.write({'state_contingency' : 'exitosa', 'resend' : False})
                        doc_send_dian.date_email_send = fields.Datetime.now()
                        doc_send_dian.xml_response_contingency_dian = 'XML de factura de contigencia enviada al cliente'
                    else:
                        doc_send_dian.write({'state_contingency' : 'rechazada', 'resend' : True})
                        doc_send_dian.xml_response_dian = ' '
                        doc_send_dian.xml_response_contingency_dian = 'XML de factura de contingencia no pudo ser enviada al cliente' 

                    # Verificar si en la DIAN todavía persiste la falla tecnológica
                    date_current = self._get_datetime()    
                    date_current = datetime.strptime(date_current, '%Y-%m-%d %H:%M:%S')
                    time_difference = date_current - company.date_init_contingency_4  
                    if time_difference.days > 0 or (time_difference.seconds / 60) > 30:                          
                        company.in_contingency_4 = False
                        company.date_end_contingency_4 = date_current
        return  


    @api.multi
    def enviar_email(self, data_xml_document, invoice_id, fileName, zipPath=False):
        _logger.info('enviar_email|start')
        user = self.env['res.users'].sudo().search([('id', '=', self.env.uid)])
        company = self.env['res.company'].sudo().search([('id', '=', user.company_id.id)])
        fileName = fileName if company.production else fileName[:-4]

        rs_invoice = self.env['account.invoice'].sudo().search([('id', '=', invoice_id)])
        dian_xml = base64.b64encode(data_xml_document.encode())
        rs_invoice.write({'archivo_xml_invoice': dian_xml})
        rs_adjunto = self.env['ir.attachment'].sudo()
        dictAdjunto = {
            'name': fileName[:-4],
            'res_id': rs_invoice.id,
            'res_model': 'account.invoice',
            'res_model_name': 'Factura',
            'res_field': 'archivo_xml_invoice',
            'mimetype': 'application/xml;charset=utf-8',
            'public': False,
            'datas_fname': fileName + '.xml',
            'res_name': fileName,
            'db_datas': dian_xml,
        }
        
        if zipPath:
            # Add Zip file at attachment
            _logger.info('enviar_email|adding Zip File')
            zip_content = self._read_zip_content(fileName + '.xml', fileName + '.zip', dian_xml, zipPath)
            dictAdjunto2 = {
                'name': fileName[:-4] + '_zip',
                'res_id': rs_invoice.id,
                'res_model': 'account.invoice',
                'res_model_name': 'Factura',
                'res_field': 'archivo_zip_invoice',
                'mimetype': 'application/zip;charset=utf-8',
                'public': False,
                'datas_fname': fileName + '.zip',
                'res_name': fileName,
                'db_datas': zip_content,
            }

            nuevo_adjunto2 = rs_adjunto.create(dictAdjunto2)
            rs_invoice.xml_adjunto_ids += nuevo_adjunto2

        nuevo_adjunto = rs_adjunto.create(dictAdjunto)
        rs_invoice.xml_adjunto_ids += nuevo_adjunto

        plantilla_correo = self.env.ref('l10n_co_e-invoice.email_template_edi_invoice_dian', False)
        if plantilla_correo:
            plantilla_correo.attachment_ids = rs_invoice.xml_adjunto_ids
            plantilla_correo.send_mail(rs_invoice.id, force_send = True)
            _logger.info('enviar_email|email sent successfully') 
        else:       
            raise ValidationError("No existe la plantilla de correo email_template_edi_invoice_dian para el email")        
        return True


    @api.multi
    def _generate_SignatureValue_GetStatus(self, document_repository, password, data_xml_SignedInfo_generate, archivo_pem, archivo_certificado):
        _logger.info('_generate_SignatureValue_GetStatus|start')
        data_xml_SignatureValue_c14n = etree.tostring(etree.fromstring(data_xml_SignedInfo_generate), method="c14n")
        #data_xml_SignatureValue_c14n = data_xml_SignatureValue_c14n.decode()
        archivo_key = document_repository+'/'+archivo_certificado
        try:
            key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)  
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        try:
            signature = crypto.sign(key.get_privatekey(), data_xml_SignatureValue_c14n, 'sha256')               
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        SignatureValue = base64.b64encode(signature).decode()
        archivo_pem = document_repository+'/'+archivo_pem
        pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        try:
            validacion = crypto.verify(pem, signature, data_xml_SignatureValue_c14n, 'sha256')
        except:
            raise ValidationError("Firma para el GestStatus no fué validada exitosamente")
        return SignatureValue


    @api.model
    def _generate_signature(self, data_xml_document, template_signature_data_xml, dian_constants, data_constants_document):
        _logger.info('_generate_signature|start')
        data_xml_keyinfo_base = ''
        data_xml_politics = ''
        data_xml_SignedProperties_base = ''
        data_xml_SigningTime = ''
        data_xml_SignatureValue = ''
        # Generar clave de referencia 0 para la firma del documento (referencia ref0)
        # Actualizar datos de signature
        #    Generar certificado publico para la firma del documento en el elemento keyinfo 
        data_public_certificate_base = dian_constants['Certificate']
        #    Generar clave de politica de firma para la firma del documento (SigPolicyHash)
        data_xml_politics = self._generate_signature_politics(dian_constants['document_repository'])
        #    Obtener la hora de Colombia desde la hora del pc
        data_xml_SigningTime = self._generate_signature_signingtime()
        #    Generar clave de referencia 0 para la firma del documento (referencia ref0)
        #    1ra. Actualización de firma ref0 (leer todo el xml sin firma)
        data_xml_signature_ref_zero = self._generate_signature_ref0(data_xml_document, dian_constants['document_repository'], dian_constants['CertificateKey'])
        data_xml_signature = self._update_signature(template_signature_data_xml,  
                                data_xml_signature_ref_zero, data_public_certificate_base, 
                                data_xml_keyinfo_base, data_xml_politics, 
                                data_xml_SignedProperties_base, data_xml_SigningTime, 
                                dian_constants, data_xml_SignatureValue, data_constants_document)
        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_signature = etree.tostring(etree.XML(data_xml_signature, parser=parser))
        data_xml_signature = data_xml_signature.decode()
        #    Actualiza Keyinfo
        KeyInfo = etree.fromstring(data_xml_signature)
        KeyInfo = etree.tostring(KeyInfo[2])
        KeyInfo = KeyInfo.decode()
        if data_constants_document['InvoiceTypeCode'] in ('01','03', '02'): # Factura
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            KeyInfo = KeyInfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        if data_constants_document['InvoiceTypeCode'] == '91': # Nota de crédito
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            KeyInfo = KeyInfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        if data_constants_document['InvoiceTypeCode'] == '92': # Nota de débito
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            KeyInfo = KeyInfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        data_xml_keyinfo_base = self._generate_signature_ref1(KeyInfo, dian_constants['document_repository'], dian_constants['CertificateKey'])        
        data_xml_signature = data_xml_signature.replace("<ds:DigestValue/>","<ds:DigestValue>%s</ds:DigestValue>" % data_xml_keyinfo_base, 1)
        #    Actualiza SignedProperties   
        SignedProperties = etree.fromstring(data_xml_signature)
        SignedProperties = etree.tostring(SignedProperties[3])
        SignedProperties = etree.fromstring(SignedProperties)
        SignedProperties = etree.tostring(SignedProperties[0])
        SignedProperties = etree.fromstring(SignedProperties)
        SignedProperties = etree.tostring(SignedProperties[0])
        SignedProperties = SignedProperties.decode()
        if data_constants_document['InvoiceTypeCode'] in ('01','03', '02'):
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            SignedProperties = SignedProperties.replace('xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        if data_constants_document['InvoiceTypeCode'] == '91':
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            SignedProperties = SignedProperties.replace('xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        if data_constants_document['InvoiceTypeCode'] == '92': # Nota de débito
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            SignedProperties = SignedProperties.replace('xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        data_xml_SignedProperties_base = self._generate_signature_ref2(SignedProperties)
        data_xml_signature = data_xml_signature.replace("<ds:DigestValue/>","<ds:DigestValue>%s</ds:DigestValue>" % data_xml_SignedProperties_base, 1)
        #    Actualiza Signeinfo
        Signedinfo = etree.fromstring(data_xml_signature)
        Signedinfo = etree.tostring(Signedinfo[0])
        Signedinfo = Signedinfo.decode()
        if data_constants_document['InvoiceTypeCode'] in ('01','03', '02'):
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            Signedinfo = Signedinfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        if data_constants_document['InvoiceTypeCode'] == '91':
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            Signedinfo = Signedinfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        if data_constants_document['InvoiceTypeCode'] == '92': # Nota de débito
            xmlns = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            Signedinfo = Signedinfo.replace('xmlns:ds="http://www.w3.org/2000/09/xmldsig#"', '%s' % xmlns )
        data_xml_SignatureValue = self._generate_SignatureValue(dian_constants['document_repository'], dian_constants['CertificateKey'], Signedinfo, dian_constants['archivo_pem'], dian_constants['archivo_certificado'])
        SignatureValue = etree.fromstring(data_xml_signature)
        SignatureValue = etree.tostring(SignatureValue[1])
        SignatureValue = SignatureValue.decode()
        data_xml_signature = data_xml_signature.replace('-sigvalue"/>','-sigvalue">%s</ds:SignatureValue>' % data_xml_SignatureValue, 1)
        return data_xml_signature


    @api.model
    def _get_dian_constants(self, data_header_doc):
        _logger.info('_get_dian_constants|start')
        company = self.env.user.company_id
        partner = company.partner_id 
        dian_constants = {}
        dian_constants['document_repository'] = company.document_repository                             # Ruta en donde se almacenaran los archivos que utiliza y genera la Facturación Electrónica
        dian_constants['Username'] = company.software_identification_code                               # Identificador del software en estado en pruebas o activo 
        dian_constants['Password'] = hashlib.new('sha256',company.password_environment.encode()).hexdigest()     # Es el resultado de aplicar la función de resumen SHA-256 sobre la contraseña del software en estado en pruebas o activo
        dian_constants['IdentificationCode'] = partner.country_id.code                                  # Identificador de pais
        dian_constants['ProviderID'] = partner.xidentification     if partner.xidentification else ''   # ID Proveedor de software o cliente si es software propio
        dian_constants['SoftwareID'] = company.software_identification_code                             # ID del software a utilizar
        dian_constants['SoftwareSecurityCode'] = self._generate_software_security_code(company.software_identification_code, 
                                                company.software_pin,data_header_doc.number)            # Código de seguridad del software: (hashlib.new('sha384', str(self.company_id.software_id) + str(self.company_id.software_pin)))
        dian_constants['PINSoftware'] = company.software_pin
        dian_constants['SeedCode'] = company.seed_code
        dian_constants['UBLVersionID'] = 'UBL 2.1'  # Versión base de UBL usada. Debe marcar UBL 2.0
        if data_header_doc.type == 'out_invoice':
            dian_constants['ProfileID'] = 'DIAN 2.1: Factura Electrónica de Venta'
        elif data_header_doc.is_debit_note:
            dian_constants['ProfileID'] = 'DIAN 2.1: Nota Débito de Factura Electrónica de Venta'
        else:
            dian_constants['ProfileID'] = 'DIAN 2.1: Nota Crédito de Factura Electrónica de Venta'


        # Versión del Formato: Indicar versión del documento. Debe usarse "DIAN 1.0"
        dian_constants['CustomizationID'] = '20'
        dian_constants['ProfileExecutionID'] = tipo_ambiente['PRODUCCION'] if company.production else tipo_ambiente['PRUEBA']                                                       # 1 = produccción 2 = prueba
        dian_constants['SupplierAdditionalAccountID'] = '1' if partner.is_company else '2'              # Persona natural o jurídica (persona natural, jurídica, gran contribuyente, otros)
        dian_constants['SupplierID'] = partner.xidentification if partner.xidentification else ''       # Identificador fiscal: En Colombia, el NIT
        dian_constants['SupplierSchemeID'] = partner.doctype
        dian_constants['SupplierPartyName'] = self._replace_character_especial(partner.name)            # Nombre Comercial
        dian_constants['SupplierDepartment'] = partner.state_id.name                                    # Ciudad o departamento (No requerido)
        dian_constants['SupplierCityCode'] = partner.xcity.code                                         # Municipio tabla 6.4.3 res.country.state.city
        dian_constants['SupplierCityName'] = partner.xcity.name                                         # Municipio tabla 6.4.3 res.country.state.city
        dian_constants['SupplierCountrySubentity'] = partner.state_id.name                              # Ciudad o departamento tabla 6.4.2 res.country.state
        dian_constants['SupplierCountrySubentityCode'] = partner.xcity.code[0:2]                          # Ciudad o departamento tabla 6.4.2 res.country.state
        dian_constants['SupplierCountryCode'] = partner.country_id.code                                 # País tabla 6.4.1 res.country
        dian_constants['SupplierCountryName'] = partner.country_id.name                                 # País tabla 6.4.1 res.country
        dian_constants['SupplierLine'] = partner.street                                                 # Calle
        dian_constants['SupplierRegistrationName'] = company.trade_name                                 # Razón Social: Obligatorio en caso de ser una persona jurídica. Razón social de la empresa
        dian_constants['schemeID'] = partner.dv                                                         # Digito verificador del NIT
        dian_constants['SupplierElectronicMail'] = partner.email
        dian_constants['SupplierTaxLevelCode'] = self._get_partner_fiscal_responsability_code(partner.id)                  # tabla 6.2.4 Régimes fiscal (listname) y 6.2.7 Responsabilidades fiscales
        dian_constants['Certificate'] = company.digital_certificate
        dian_constants['NitSinDV'] = partner.xidentification 
        dian_constants['CertificateKey'] = company.certificate_key 
        dian_constants['archivo_pem'] = company.pem
        dian_constants['archivo_certificado'] = company.certificate
        dian_constants['CertDigestDigestValue'] = self._generate_CertDigestDigestValue(company.digital_certificate, dian_constants['CertificateKey'], dian_constants['document_repository'], dian_constants['archivo_certificado']) 
        dian_constants['IssuerName'] = company.issuer_name                                              # Nombre del proveedor del certificado
        dian_constants['SerialNumber'] = company.serial_number                                          # Serial del certificado
        dian_constants['TaxSchemeID'] = partner.tribute_id.code
        dian_constants['TaxSchemeName'] = partner.tribute_id.name
        dian_constants['Currency'] = company.currency_id.id
        dian_constants['SupplierCityNameSubentity'] = partner.xcity.name
        dian_constants['DeliveryAddress'] = partner.partner_shipping_id.street if hasattr(partner, 'hasattr') else partner.street


        return dian_constants


    def _generate_data_constants_document(self, data_header_doc, dian_constants, document_type, in_contingency_4):
        _logger.info('_generate_data_constants_document|start')
        NitSinDV = dian_constants['NitSinDV']
        data_constants_document = {}
        data_resolution  = self._get_resolution_dian(data_header_doc)
        # Generar nombre del archvio xml
        data_constants_document['FileNameXML'] = self._generate_xml_filename(data_resolution, NitSinDV, data_header_doc.type, data_header_doc.is_debit_note)
        data_constants_document['FileNameZIP'] = self._generate_zip_filename(data_resolution, NitSinDV, data_header_doc.type, data_header_doc.is_debit_note)
        data_constants_document['InvoiceAuthorization'] = data_resolution['InvoiceAuthorization']                           # Número de resolución
        data_constants_document['StartDate'] = data_resolution['StartDate']                                                 # Fecha desde resolución
        data_constants_document['EndDate'] = data_resolution['EndDate']                                                     # Fecha hasta resolución
        data_constants_document['Prefix'] = data_resolution['Prefix']  # Prefijo de número de factura
        if data_header_doc.type != 'out_invoice':
            data_constants_document['Prefix'] = data_resolution['InvoiceID']

        data_constants_document['From'] = data_resolution['From']                                                           # Desde la secuencia
        data_constants_document['To'] = data_resolution['To']                                                               # Hasta la secuencia
        data_constants_document['InvoiceID'] = data_resolution['InvoiceID'] 
        data_constants_document['ContingencyID'] = data_resolution['ContingencyID'] if document_type == 'contingency' else ' '                                               # Número de documento dian
        data_constants_document['Nonce'] = self._generate_nonce(data_resolution['InvoiceID'], dian_constants['SeedCode'])   # semilla para generar números aleatorios
        data_constants_document['TechnicalKey'] = data_resolution['TechnicalKey']                                           # Clave técnica de la resolución de rango
        data_constants_document['LineExtensionAmount'] = self._complements_second_decimal_total(data_header_doc.amount_untaxed)   # Total Importe bruto antes de impuestos: Total importe bruto, suma de los importes brutos de las líneas de la factura.
        # Valor bruto más tributos
        #data_constants_document['TotalTaxInclusiveAmount'] = self._caculate_TotalTaxInclusiveAmount(data_header_doc.amount_untaxed, data_header_doc.id)

        data_constants_document['TotalTaxInclusiveAmount'] = self._complements_second_decimal_total(data_header_doc.amount_without_wh_tax) 
        #data_constants_document['TaxExclusiveAmount'] = self._complements_second_decimal_total(data_header_doc.amount_untaxed if data_header_doc.amount_tax != 0.00 else 0.00)    # Total Base Imponible (Importe Bruto+Cargos-Descuentos): Base imponible para el cálculo de los impuestos
        
        data_constants_document['TaxExclusiveAmount'] = self._caculate_TaxExclusiveAmount(data_header_doc.id)
        
        #data_constants_document['TotalTaxInclusiveAmount'] = self._complements_second_decimal_total(data_header_doc.amount_total) 
        data_constants_document['TaxExclusiveAmount'] = self._complements_second_decimal_total(data_constants_document['TaxExclusiveAmount'])    # Total Base Imponible (Importe Bruto+Cargos-Descuentos): Base imponible para el cálculo de los impuestos
        # Valor Bruto más tributos - Valor del Descuento Total + Valor del Cargo Total - Valor del Anticipo Total
        data_constants_document['PayableAmount'] = self._complements_second_decimal_total(data_header_doc.amount_without_wh_tax)   # Total de Factura: Total importe bruto + Total Impuestos-Total Impuesto Retenidos
        #data_constants_document['PayableAmount'] = self._complements_second_decimal_total(data_header_doc.amount_total)           # Total de Factura: Total importe bruto + Total Impuestos-Total Impuesto Retenidos
        date_invoice_cufe = self._generate_datetime_IssueDate()
        data_constants_document['IssueDate'] = date_invoice_cufe['IssueDate']                                               # Fecha de emisión de la factura a efectos fiscales        
        data_constants_document['IssueDateSend'] = date_invoice_cufe['IssueDateSend']
        data_constants_document['IssueDateCufe'] = date_invoice_cufe['IssueDateCufe']
        data_constants_document['IssueTime'] = self._get_time_colombia()                                                             # Hora de emisión de la fcatura
        data_constants_document['InvoiceTypeCode'] = self._get_doctype(data_header_doc.type, data_header_doc.is_debit_note, in_contingency_4)
        data_constants_document['CreditNoteTypeCode'] = self._get_doctype(data_header_doc.type, data_header_doc.is_debit_note, in_contingency_4)
        data_constants_document['DebitNoteTypeCode'] = self._get_doctype(data_header_doc.type, data_header_doc.is_debit_note, in_contingency_4)                                 # Tipo de Factura, código: facturas de venta, y transcripciones; tipo = 1 para factura de venta 
        data_constants_document['LineCountNumeric'] = self._get_lines_invoice(data_header_doc.id)
        data_constants_document['TaxSchemeID'] = data_header_doc.partner_id.tribute_id.code
        data_constants_document['TaxSchemeName'] = data_header_doc.partner_id.tribute_id.name
        data_constants_document['DocumentCurrencyCode'] = data_header_doc.currency_id.name                                  # Divisa de la Factura
        data_constants_document['CustomerAdditionalAccountID'] = '1' if data_header_doc.partner_id.is_company else '2'
        # ini Modificado 28JUL20 ver xmls modificados
        if data_header_doc.partner_id.doctype == 31:
            data_constants_document['IDAdquiriente'] = data_header_doc.partner_id.xidentification if data_header_doc.partner_id.xidentification else ''
            data_constants_document['SchemeNameAdquiriente'] = data_header_doc.partner_id.doctype
            data_constants_document['SchemeIDAdquiriente'] = data_header_doc.partner_id.dv 
        else:
            data_constants_document['IDAdquiriente'] = data_header_doc.partner_id.xidentification if data_header_doc.partner_id.xidentification else ''
            data_constants_document['SchemeNameAdquiriente'] = data_header_doc.partner_id.doctype
            data_constants_document['SchemeIDAdquiriente'] = ''
        # fin Modificado 28JUL20
        data_constants_document['CustomerID'] = data_header_doc.partner_id.xidentification if data_header_doc.partner_id.xidentification else '' # Identificador fiscal: En Colombia, el NIT
        data_constants_document['CustomerSchemeID'] = data_header_doc.partner_id.doctype                                    # tipo de identificdor fiscal 
        data_constants_document['CustomerPartyName'] = self._replace_character_especial(data_header_doc.partner_id.name)                                      # Nombre Comercial
        data_constants_document['CustomerDepartment'] = data_header_doc.partner_id.state_id.name if data_header_doc.partner_id.state_id.name else ''
        data_constants_document['CustomerCityCode'] = data_header_doc.partner_id.xcity.code                 # Municipio tabla 6.4.3 res.country.state.city
        data_constants_document['CustomerCityName'] = data_header_doc.partner_id.xcity.name                 # Municipio tabla 6.4.3 res.country.state.city
        data_constants_document['CustomerCountrySubentity'] = data_header_doc.partner_id.state_id.name      # Ciudad o departamento tabla 6.4.2 res.country.state
        data_constants_document['CustomerCountrySubentityCode'] = data_header_doc.partner_id.xcity.code[0:2]  # Ciudad o departamento tabla 6.4.2 res.country.state
        data_constants_document['CustomerCountryCode'] = data_header_doc.partner_id.country_id.code         # País tabla 6.4.1 res.country
        data_constants_document['CustomerCountryName'] = data_header_doc.partner_id.country_id.name         # País tabla 6.4.1 res.country
        data_constants_document['CustomerAddressLine'] = data_header_doc.partner_id.street
        data_constants_document['CustomerTaxLevelCode'] = self._get_partner_fiscal_responsability_code(data_header_doc.partner_id.id)
        data_constants_document['CustomerRegistrationName'] = self._replace_character_especial(data_header_doc.partner_id.companyName)
        data_constants_document['CustomerEmail'] = data_header_doc.partner_id.email if data_header_doc.partner_id.email else ''
        data_constants_document['CustomerLine'] = data_header_doc.partner_id.street
        data_constants_document['CustomerElectronicMail'] = data_header_doc.partner_id.email
        data_constants_document['CustomerschemeID'] = data_header_doc.partner_id.dv                         # Digito verificador del NIT
        data_constants_document['Firstname'] = self._replace_character_especial(data_header_doc.partner_id.name)
        data_constants_document['CurrencyID'] = data_header_doc.currency_id.name
        # Obtener la tasa de cambio
        if dian_constants['Currency'] == data_header_doc.currency_id.id:
            data_constants_document['CalculationRate'] = 1.00
        else:
            data_constants_document['CalculationRate'] = self._get_rate_date(data_header_doc.company_id.id,data_header_doc.currency_id.id,data_header_doc.date_invoice)
            data_constants_document['CalculationRate'] = self._complements_second_decimal_total(data_constants_document['CalculationRate'])
        # Obtener la fecha de cambio
        data_constants_document['DateRate'] = data_header_doc.date_invoice
        # Determina termino de pago 1 Contado 2 Crédito
        if not data_header_doc.payment_term_id.line_ids:
            data_constants_document['PaymentMeansID'] =  '1'  
            data_constants_document['PaymentDueDate'] = data_header_doc.date_invoice
        for line_term_pago in data_header_doc.payment_term_id.line_ids:
            if line_term_pago.days == 0:
                data_constants_document['PaymentMeansID'] =  '1'  
                data_constants_document['PaymentDueDate'] = data_header_doc.date_invoice
            else:
                data_constants_document['PaymentMeansID'] =  '2'
                # Listo falta Fecha de vencimiento de la factura Obligatorio si es venta a crédito (0)  
                data_constants_document['PaymentDueDate'] = data_header_doc.date_due
        # Ojo Falta Código correspondiente al medio de pago Lista de valores 6.3.4.2 (1)
        # Por defecto medio de pago 1 Instrumento no definido
        data_constants_document['PaymentMeansCode'] = '1'
        # Datos nota de crédito y débito
        if data_constants_document['InvoiceTypeCode'] in ('91','92'):
            #invoice_cancel = self.env['account.invoice'].search([('move_name', '=', data_header_doc.origin),('type', '=', 'out_invoice'),('diancode_id', '!=', False)])
            invoice_cancel = self.env['account.invoice'].search([('move_name', '=', data_header_doc.origin),('type', '=', 'out_invoice'),('state_dian_document', '=', 'exitoso')])
            if invoice_cancel:
                dian_document_cancel = self.env['dian.document'].search([('state', '=', 'exitoso'),('document_type', '=', 'f'),('id', '=', invoice_cancel.diancode_id.id)])
                if dian_document_cancel:
                    data_constants_document['InvoiceReferenceID'] = dian_document_cancel.dian_code
                    data_constants_document['InvoiceReferenceUUID'] = dian_document_cancel.cufe
                    data_constants_document['InvoiceReferenceDate'] = invoice_cancel.date_invoice
        # Datos contingencia
        if data_constants_document['InvoiceTypeCode'] == ('03'):
            data_constants_document['ContingencyReferenceID'] = data_header_doc.contingency_invoice_number
            data_constants_document['ContingencyIssueDate'] = data_header_doc.date_invoice
            data_constants_document['ContingencyDocumentTypeCode'] = 'FTC'

        # Genera identificadores único 
        identifier = uuid.uuid4()
        data_constants_document['identifier'] = identifier
        identifierkeyinfo = uuid.uuid4()
        data_constants_document['identifierkeyinfo'] = identifierkeyinfo

        data_constants_document['ResponseCodeCreditNote'] = data_header_doc.concepto_credit_note
        data_constants_document['ResponseCodeDebitNote'] = data_header_doc.concept_debit_note
        data_constants_document['DescriptionDebitCreditNote'] = data_header_doc.name

        return data_constants_document


    def _replace_character_especial(self, constant):
        if constant:
            constant = constant.replace('&','&amp;')
            constant = constant.replace('<','&lt;')
            constant = constant.replace('>','&gt;')
            constant = constant.replace('"','&quot;')
            constant = constant.replace("'",'&apos;')
        return constant


    def _get_partner_fiscal_responsability_code(self,partner_id):
        _logger.info('_get_partner_fiscal_responsability_code|start')
        rec_partner = self.env['res.partner'].search([('id', '=', partner_id)])
        fiscal_responsability_codes = ''
        if rec_partner:
            for fiscal_responsability in rec_partner.fiscal_responsability_ids:
                fiscal_responsability_codes += ';' + fiscal_responsability.code if fiscal_responsability_codes else fiscal_responsability.code
        return fiscal_responsability_codes


    def _caculate_TaxExclusiveAmount(self, invoice_id):
        amount_untaxed = 0.00
        data_lines_doc = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)])
        for data_line_doc in data_lines_doc:
            if data_line_doc.invoice_line_tax_ids:
                amount_untaxed += data_line_doc.price_subtotal
        return amount_untaxed


    # def _caculate_TotalTaxInclusiveAmount(self, amount_untaxed, invoice_id):
    #     data_tax_detail_doc = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice_id)])
    #     iva_01 = 0.00
    #     ica_03 = 0.00
    #     inc_04 = 0.00
    #     if data_tax_detail_doc:
    #         for item_tax in data_tax_detail_doc:
    #             iva_01 += item_tax.amount if item_tax.tax_id.tax_group_fe == 'iva_fe' else 0.0
    #             ica_03 += item_tax.amount if item_tax.tax_id.tax_group_fe == 'ica_fe' else 0.0
    #             inc_04 += item_tax.amount if item_tax.tax_id.tax_group_fe == 'ico_fe' else 0.0 
    #     # iva_01 = iva_01 if iva_01 >= 0.00 else iva_01 * -1
    #     # ica_03 = ica_03 if ica_03 >= 0.00 else ica_03 * -1
    #     # inc_04 = inc_04 if inc_04 >= 0.00 else inc_04 * -1
    #     TotalTaxInclusiveAmount = amount_untaxed + iva_01 + ica_03 + inc_04
    #     return TotalTaxInclusiveAmount


    def _template_basic_data_fe_xml(self):
        template_basic_data_fe_xml = """
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2    http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-Invoice-2.1.xsd">
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
                        <cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1">%(IdentificationCode)s</cbc:IdentificationCode>
                    </sts:InvoiceSource>
                    <sts:SoftwareProvider>
                        <sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</sts:ProviderID>
                        <sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareID)s</sts:SoftwareID>
                    </sts:SoftwareProvider>
                    <sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareSecurityCode)s</sts:SoftwareSecurityCode>
                    <sts:AuthorizationProvider>
                        <sts:AuthorizationProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="4" schemeName="31">800197268</sts:AuthorizationProviderID>
                    </sts:AuthorizationProvider>
                    <sts:QRCode>URL=https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentKey=%(UUID)s</sts:QRCode>
                </sts:DianExtensions>
            </ext:ExtensionContent>
        </ext:UBLExtension>   
        <ext:UBLExtension>
            <ext:ExtensionContent></ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>
   <cbc:UBLVersionID>%(UBLVersionID)s</cbc:UBLVersionID>
   <cbc:CustomizationID>%(CustomizationID)s</cbc:CustomizationID>
   <cbc:ProfileID>%(ProfileID)s</cbc:ProfileID>
   <cbc:ProfileExecutionID>%(ProfileExecutionID)s</cbc:ProfileExecutionID>
   <cbc:ID>%(InvoiceID)s</cbc:ID>
   <cbc:UUID schemeID="%(ProfileExecutionID)s" schemeName="CUFE-SHA384">%(UUID)s</cbc:UUID>
   <cbc:IssueDate>%(IssueDate)s</cbc:IssueDate>
   <cbc:IssueTime>%(IssueTime)s</cbc:IssueTime>
   <cbc:InvoiceTypeCode>%(InvoiceTypeCode)s</cbc:InvoiceTypeCode>
   <cbc:DocumentCurrencyCode>%(DocumentCurrencyCode)s</cbc:DocumentCurrencyCode>
   <cbc:LineCountNumeric>%(LineCountNumeric)s</cbc:LineCountNumeric>
   <cac:AccountingSupplierParty>
      <cbc:AdditionalAccountID>%(SupplierAdditionalAccountID)s</cbc:AdditionalAccountID>
      <cac:Party>
         <cac:PartyName>
            <cbc:Name>%(SupplierPartyName)s</cbc:Name>
         </cac:PartyName>
         <cac:PhysicalLocation>
            <cac:Address>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:Address>
         </cac:PhysicalLocation>
         <cac:PartyTaxScheme>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cbc:TaxLevelCode listName="48">%(SupplierTaxLevelCode)s</cbc:TaxLevelCode>
            <cac:RegistrationAddress>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:RegistrationAddress>
            <cac:TaxScheme>
               <cbc:ID>%(TaxSchemeID)s</cbc:ID>
               <cbc:Name>%(TaxSchemeName)s</cbc:Name>
            </cac:TaxScheme>
         </cac:PartyTaxScheme>
         <cac:PartyLegalEntity>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cac:CorporateRegistrationScheme>
               <cbc:ID>%(Prefix)s</cbc:ID>
            </cac:CorporateRegistrationScheme>
         </cac:PartyLegalEntity>
         <cac:Contact>
           <cbc:ElectronicMail>%(SupplierElectronicMail)s</cbc:ElectronicMail>
         </cac:Contact>   
      </cac:Party>
   </cac:AccountingSupplierParty>
   <cac:AccountingCustomerParty>
      <cbc:AdditionalAccountID>%(CustomerAdditionalAccountID)s</cbc:AdditionalAccountID>
      <cac:Party>
         <cac:PartyIdentification>
            <cbc:ID schemeName="%(SchemeNameAdquiriente)s" schemeID="%(SchemeIDAdquiriente)s">%(IDAdquiriente)s</cbc:ID>                        
         </cac:PartyIdentification>
         <cac:PartyName>
            <cbc:Name>%(CustomerPartyName)s</cbc:Name>
         </cac:PartyName>
         <cac:PhysicalLocation>
            <cac:Address>
               <cbc:ID>%(CustomerCityCode)s</cbc:ID>
               <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(CustomerLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
               </cac:Country>
            </cac:Address>
         </cac:PhysicalLocation>
         <cac:PartyTaxScheme>
            <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
            <cbc:TaxLevelCode listName="48">%(CustomerTaxLevelCode)s</cbc:TaxLevelCode>
            <cac:RegistrationAddress>
               <cbc:ID>%(CustomerCityCode)s</cbc:ID>
               <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(CustomerLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
               </cac:Country>
            </cac:RegistrationAddress>
            <cac:TaxScheme>
               <cbc:ID>%(TaxSchemeID)s</cbc:ID>
               <cbc:Name>%(TaxSchemeName)s</cbc:Name>
            </cac:TaxScheme>
         </cac:PartyTaxScheme>
         <cac:PartyLegalEntity>
            <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
        </cac:PartyLegalEntity>
        <cac:Contact>
           <cbc:ElectronicMail>%(CustomerElectronicMail)s</cbc:ElectronicMail>
        </cac:Contact>
        <cac:Person>
           <cbc:FirstName>%(Firstname)s</cbc:FirstName>
        </cac:Person>
      </cac:Party>
   </cac:AccountingCustomerParty>
   <cac:PaymentMeans>
      <cbc:ID>%(PaymentMeansID)s</cbc:ID>
      <cbc:PaymentMeansCode>%(PaymentMeansCode)s</cbc:PaymentMeansCode>
      <cbc:PaymentDueDate>%(PaymentDueDate)s</cbc:PaymentDueDate>
      <cbc:PaymentID>1234</cbc:PaymentID>      
   </cac:PaymentMeans>
   <cac:PaymentExchangeRate>
      <cbc:SourceCurrencyCode>%(CurrencyID)s</cbc:SourceCurrencyCode>
      <cbc:SourceCurrencyBaseRate>1.00</cbc:SourceCurrencyBaseRate>
      <cbc:TargetCurrencyCode>COP</cbc:TargetCurrencyCode>
      <cbc:TargetCurrencyBaseRate>1.00</cbc:TargetCurrencyBaseRate>
      <cbc:CalculationRate>%(CalculationRate)s</cbc:CalculationRate>
      <cbc:Date>%(DateRate)s</cbc:Date>
   </cac:PaymentExchangeRate>%(data_taxs_xml)s
   <cac:LegalMonetaryTotal>   
      <cbc:LineExtensionAmount currencyID="%(CurrencyID)s">%(TotalLineExtensionAmount)s</cbc:LineExtensionAmount>
      <cbc:TaxExclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxExclusiveAmount)s</cbc:TaxExclusiveAmount>
      <cbc:TaxInclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxInclusiveAmount)s</cbc:TaxInclusiveAmount>
      <cbc:PayableAmount currencyID="%(CurrencyID)s">%(PayableAmount)s</cbc:PayableAmount>
   </cac:LegalMonetaryTotal>%(data_lines_xml)s

   
</Invoice>
"""
        return template_basic_data_fe_xml


    def _template_basic_data_fe_exportacion_xml(self):
        template_basic_data_fe_exportacion_xml = """
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2    http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-Invoice-2.1.xsd">
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
                        <cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1">%(IdentificationCode)s</cbc:IdentificationCode>
                    </sts:InvoiceSource>
                    <sts:SoftwareProvider>
                        <sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</sts:ProviderID>
                        <sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareID)s</sts:SoftwareID>
                    </sts:SoftwareProvider>
                    <sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareSecurityCode)s</sts:SoftwareSecurityCode>
                    <sts:AuthorizationProvider>
                        <sts:AuthorizationProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="4" schemeName="31">800197268</sts:AuthorizationProviderID>
                    </sts:AuthorizationProvider>
                    <sts:QRCode>URL=https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentKey=%(UUID)s</sts:QRCode>
                </sts:DianExtensions>
            </ext:ExtensionContent>
        </ext:UBLExtension>   
        <ext:UBLExtension>
            <ext:ExtensionContent></ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>
   <cbc:UBLVersionID>%(UBLVersionID)s</cbc:UBLVersionID>
   <cbc:CustomizationID>%(CustomizationID)s</cbc:CustomizationID>
   <cbc:ProfileID>%(ProfileID)s</cbc:ProfileID>
   <cbc:ProfileExecutionID>%(ProfileExecutionID)s</cbc:ProfileExecutionID>
   <cbc:ID>%(InvoiceID)s</cbc:ID>
   <cbc:UUID schemeID="%(ProfileExecutionID)s" schemeName="CUFE-SHA384">%(UUID)s</cbc:UUID>
   <cbc:IssueDate>%(IssueDate)s</cbc:IssueDate>
   <cbc:IssueTime>%(IssueTime)s</cbc:IssueTime>
   <cbc:InvoiceTypeCode>%(InvoiceTypeCode)s</cbc:InvoiceTypeCode>
   <cbc:DocumentCurrencyCode>%(DocumentCurrencyCode)s</cbc:DocumentCurrencyCode>
   <cbc:LineCountNumeric>%(LineCountNumeric)s</cbc:LineCountNumeric>
   <cac:AccountingSupplierParty>
      <cbc:AdditionalAccountID>%(SupplierAdditionalAccountID)s</cbc:AdditionalAccountID>
      <cac:Party>
         <cac:PartyName>
            <cbc:Name>%(SupplierPartyName)s</cbc:Name>
         </cac:PartyName>
         <cac:PhysicalLocation>
            <cac:Address>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:Address>
         </cac:PhysicalLocation>
         <cac:PartyTaxScheme>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cbc:TaxLevelCode listName="48">%(SupplierTaxLevelCode)s</cbc:TaxLevelCode>
            <cac:RegistrationAddress>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:RegistrationAddress>
            <cac:TaxScheme>
               <cbc:ID>%(TaxSchemeID)s</cbc:ID>
               <cbc:Name>%(TaxSchemeName)s</cbc:Name>
            </cac:TaxScheme>
         </cac:PartyTaxScheme>
         <cac:PartyLegalEntity>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cac:CorporateRegistrationScheme>
               <cbc:ID>%(Prefix)s</cbc:ID>
            </cac:CorporateRegistrationScheme>
         </cac:PartyLegalEntity>
         <cac:Contact>
           <cbc:ElectronicMail>%(SupplierElectronicMail)s</cbc:ElectronicMail>
         </cac:Contact>   
      </cac:Party>
   </cac:AccountingSupplierParty>
   <cac:AccountingCustomerParty>
      <cbc:AdditionalAccountID>%(CustomerAdditionalAccountID)s</cbc:AdditionalAccountID>
      <cac:Party>
         <cac:PartyIdentification>
            <cbc:ID schemeName="%(SchemeNameAdquiriente)s" schemeID="%(SchemeIDAdquiriente)s">%(IDAdquiriente)s</cbc:ID>                        
         </cac:PartyIdentification>
         <cac:PartyName>
            <cbc:Name>%(CustomerPartyName)s</cbc:Name>
         </cac:PartyName>
         <cac:PhysicalLocation>
            <cac:Address>
               <cbc:ID>%(CustomerCityCode)s</cbc:ID>
               <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(CustomerLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
               </cac:Country>
            </cac:Address>
         </cac:PhysicalLocation>
         <cac:PartyTaxScheme>
            <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
            <cbc:TaxLevelCode listName="48">%(CustomerTaxLevelCode)s</cbc:TaxLevelCode>
            <cac:RegistrationAddress>
               <cbc:ID>%(CustomerCityCode)s</cbc:ID>
               <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(CustomerLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
               </cac:Country>
            </cac:RegistrationAddress>
            <cac:TaxScheme>
               <cbc:ID>%(TaxSchemeID)s</cbc:ID>
               <cbc:Name>%(TaxSchemeName)s</cbc:Name>
            </cac:TaxScheme>
         </cac:PartyTaxScheme>
         <cac:PartyLegalEntity>
            <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
        </cac:PartyLegalEntity>
        <cac:Contact>
           <cbc:ElectronicMail>%(CustomerElectronicMail)s</cbc:ElectronicMail>
        </cac:Contact>
        <cac:Person>
           <cbc:FirstName>%(Firstname)s</cbc:FirstName>
        </cac:Person>
      </cac:Party>
   </cac:AccountingCustomerParty>
   <cac:PaymentMeans>
      <cbc:ID>%(PaymentMeansID)s</cbc:ID>
      <cbc:PaymentMeansCode>%(PaymentMeansCode)s</cbc:PaymentMeansCode>
      <cbc:PaymentDueDate>%(PaymentDueDate)s</cbc:PaymentDueDate>
      <cbc:PaymentID>1234</cbc:PaymentID>      
   </cac:PaymentMeans>
   <cac:PaymentExchangeRate>
      <cbc:SourceCurrencyCode>%(CurrencyID)s</cbc:SourceCurrencyCode>
      <cbc:SourceCurrencyBaseRate>1.00</cbc:SourceCurrencyBaseRate>
      <cbc:TargetCurrencyCode>COP</cbc:TargetCurrencyCode>
      <cbc:TargetCurrencyBaseRate>1.00</cbc:TargetCurrencyBaseRate>
      <cbc:CalculationRate>%(CalculationRate)s</cbc:CalculationRate>
      <cbc:Date>%(DateRate)s</cbc:Date>
   </cac:PaymentExchangeRate>%(data_taxs_xml)s
   <cac:LegalMonetaryTotal>
      <cbc:LineExtensionAmount currencyID="%(CurrencyID)s">%(TotalLineExtensionAmount)s</cbc:LineExtensionAmount>
      <cbc:TaxExclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxExclusiveAmount)s</cbc:TaxExclusiveAmount>
      <cbc:TaxInclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxInclusiveAmount)s</cbc:TaxInclusiveAmount>
      <cbc:PayableAmount currencyID="%(CurrencyID)s">%(PayableAmount)s</cbc:PayableAmount>
   </cac:LegalMonetaryTotal>%(data_lines_xml)s
</Invoice>
"""
        return template_basic_data_fe_exportacion_xml


    def _generate_data_fe_document_xml(self, template_basic_data_fe_xml, dc, dcd, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature):
        template_basic_data_fe_xml = template_basic_data_fe_xml % {'InvoiceAuthorization' : dcd['InvoiceAuthorization'],
            'StartDate' : dcd['StartDate'],
            'EndDate' : dcd['EndDate'],
            'Prefix' : dcd['Prefix'],
            'From' : dcd['From'],
            'To' : dcd['To'],
            'IdentificationCode' : dc['IdentificationCode'],
            'ProviderID' : dc['ProviderID'],
            'SoftwareID' : dc['SoftwareID'],
            'SoftwareSecurityCode' : dc['SoftwareSecurityCode'],
            'UUID' : CUFE,            
            'UBLVersionID' : dc['UBLVersionID'],
            'CustomizationID' : dc['CustomizationID'],
            'ProfileID' : dc['ProfileID'], 
            'ProfileExecutionID' : dc['ProfileExecutionID'],                       
            'InvoiceID' : dcd['InvoiceID'],            
            'IssueDate' : dcd['IssueDate'],
            'IssueTime' : dcd['IssueTime'],
            'InvoiceTypeCode' : dcd['InvoiceTypeCode'],
            'DocumentCurrencyCode' : dcd['DocumentCurrencyCode'],
            'LineCountNumeric' : dcd['LineCountNumeric'],
            'SupplierAdditionalAccountID' : dc['SupplierAdditionalAccountID'],
            'SupplierPartyName' : dc['SupplierPartyName'],
            'SupplierCityCode' : dc['SupplierCityCode'],
            'SupplierCityName' : dc['SupplierCityName'],
            'SupplierCountrySubentity' : dc['SupplierCountrySubentity'],
            'SupplierCountrySubentityCode' : dc['SupplierCountrySubentityCode'],
            'SupplierLine' : dc['SupplierLine'],
            'SupplierCountryCode' : dc['SupplierCountryCode'],
            'SupplierCountryName' : dc['SupplierCountryName'],
            'schemeID' : dc['schemeID'],
            'SupplierTaxLevelCode' : dc['SupplierTaxLevelCode'],
            'TaxSchemeID' : dcd['TaxSchemeID'],
            'TaxSchemeName' : dcd['TaxSchemeName'],
            'SupplierElectronicMail' : dc['SupplierElectronicMail'],
            'CustomerAdditionalAccountID' : dcd['CustomerAdditionalAccountID'],
            'CustomerPartyName' : dcd['CustomerPartyName'],
            'CustomerschemeID' : dcd['CustomerschemeID'],
            'CustomerCityCode' : dcd['CustomerCityCode'],
            'CustomerCityName' : dcd['CustomerCityName'],
            'CustomerCountrySubentity' : dcd['CustomerCountrySubentity'],
            'CustomerCountrySubentityCode' : dcd['CustomerCountrySubentityCode'],
            'CustomerLine' : dcd['CustomerLine'],
            'CustomerCountryCode' : dcd['CustomerCountryCode'],            
            'CustomerCountryName' : dcd['CustomerCountryName'],
            'CustomerSchemeID' : dcd['CustomerSchemeID'],
            'CustomerID' : dcd['CustomerID'],
            'CustomerTaxLevelCode' : dcd['CustomerTaxLevelCode'],
            'CustomerElectronicMail' : dcd['CustomerElectronicMail'],
            'Firstname' : dcd['Firstname'],
            'PaymentMeansID' : dcd['PaymentMeansID'], 
            'PaymentMeansCode' : dcd['PaymentMeansCode'], 
            'PaymentDueDate' : dcd['PaymentDueDate'],
            'data_taxs_xml' : data_taxs_xml,
            'TotalLineExtensionAmount' : dcd['LineExtensionAmount'],
            'TotalTaxExclusiveAmount' : dcd['TaxExclusiveAmount'],
            'TotalTaxInclusiveAmount' : dcd['TotalTaxInclusiveAmount'],
            'PayableAmount' : dcd['PayableAmount'], 
            'data_lines_xml' : data_lines_xml,
            'CurrencyID' : dcd['CurrencyID'],
            'CalculationRate' : dcd['CalculationRate'],
            'DateRate' : dcd['DateRate'],
            'SchemeIDAdquiriente' : dcd['SchemeIDAdquiriente'],
            'SchemeNameAdquiriente' : dcd['SchemeNameAdquiriente'],
            'IDAdquiriente' : dcd['IDAdquiriente'],
            'SupplierCityNameSubentity': dc['SupplierCityNameSubentity'],
            'DeliveryAddress': dc['DeliveryAddress'],
            }
        return template_basic_data_fe_xml


    def _template_basic_data_contingencia_xml(self):
        template_basic_data_contingencia_xml = """
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2    http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-Invoice-2.1.xsd">
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
                        <cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1">%(IdentificationCode)s</cbc:IdentificationCode>
                    </sts:InvoiceSource>
                    <sts:SoftwareProvider>
                        <sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</sts:ProviderID>
                        <sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareID)s</sts:SoftwareID>
                    </sts:SoftwareProvider>
                    <sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareSecurityCode)s</sts:SoftwareSecurityCode>
                    <sts:AuthorizationProvider>
                        <sts:AuthorizationProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="4" schemeName="31">800197268</sts:AuthorizationProviderID>
                    </sts:AuthorizationProvider>
                    <sts:QRCode>URL=https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentKey=%(UUID)s</sts:QRCode>
                </sts:DianExtensions>
            </ext:ExtensionContent>
        </ext:UBLExtension>   
        <ext:UBLExtension>
            <ext:ExtensionContent></ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>
   <cbc:UBLVersionID>%(UBLVersionID)s</cbc:UBLVersionID>
   <cbc:CustomizationID>%(CustomizationID)s</cbc:CustomizationID>
   <cbc:ProfileID>%(ProfileID)s</cbc:ProfileID>
   <cbc:ProfileExecutionID>%(ProfileExecutionID)s</cbc:ProfileExecutionID>
   <cbc:ID>%(ContingencyID)s</cbc:ID>
   <cbc:UUID schemeID="%(ProfileExecutionID)s" schemeName="CUDE-SHA384">%(UUID)s</cbc:UUID>
   <cbc:IssueDate>%(IssueDate)s</cbc:IssueDate>
   <cbc:IssueTime>%(IssueTime)s</cbc:IssueTime>
   <cbc:InvoiceTypeCode>%(InvoiceTypeCode)s</cbc:InvoiceTypeCode>
   <cbc:DocumentCurrencyCode>%(DocumentCurrencyCode)s</cbc:DocumentCurrencyCode>
   <cbc:LineCountNumeric>%(LineCountNumeric)s</cbc:LineCountNumeric>
   <cac:AdditionalDocumentReference> 
      <cbc:ID>%(ContingencyReferenceID)s</cbc:ID>
      <cbc:IssueDate>%(ContingencyIssueDate)s</cbc:IssueDate>
      <cbc:DocumentTypeCode>%(ContingencyDocumentTypeCode)s</cbc:DocumentTypeCode>
   </cac:AdditionalDocumentReference>
   <cac:AccountingSupplierParty>
      <cbc:AdditionalAccountID>%(SupplierAdditionalAccountID)s</cbc:AdditionalAccountID>
      <cac:Party>
         <cac:PartyName>
            <cbc:Name>%(SupplierPartyName)s</cbc:Name>
         </cac:PartyName>
         <cac:PhysicalLocation>
            <cac:Address>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:Address>
         </cac:PhysicalLocation>
         <cac:PartyTaxScheme>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cbc:TaxLevelCode listName="48">%(SupplierTaxLevelCode)s</cbc:TaxLevelCode>
            <cac:RegistrationAddress>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:RegistrationAddress>
            <cac:TaxScheme>
               <cbc:ID>%(TaxSchemeID)s</cbc:ID>
               <cbc:Name>%(TaxSchemeName)s</cbc:Name>
            </cac:TaxScheme>
         </cac:PartyTaxScheme>
         <cac:PartyLegalEntity>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cac:CorporateRegistrationScheme>
               <cbc:ID>%(Prefix)s</cbc:ID>
            </cac:CorporateRegistrationScheme>
         </cac:PartyLegalEntity>
         <cac:Contact>
           <cbc:ElectronicMail>%(SupplierElectronicMail)s</cbc:ElectronicMail>
         </cac:Contact>   
      </cac:Party>
   </cac:AccountingSupplierParty>
   <cac:AccountingCustomerParty>
      <cbc:AdditionalAccountID>%(CustomerAdditionalAccountID)s</cbc:AdditionalAccountID>
      <cac:Party>
         <cac:PartyIdentification>
            <cbc:ID schemeName="%(SchemeNameAdquiriente)s" schemeID="%(SchemeIDAdquiriente)s">%(IDAdquiriente)s</cbc:ID>                        
         </cac:PartyIdentification>
         <cac:PartyName>
            <cbc:Name>%(CustomerPartyName)s</cbc:Name>
         </cac:PartyName>
         <cac:PhysicalLocation>
            <cac:Address>
               <cbc:ID>%(CustomerCityCode)s</cbc:ID>
               <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(CustomerLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
               </cac:Country>
            </cac:Address>
         </cac:PhysicalLocation>
         <cac:PartyTaxScheme>
            <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
            <cbc:TaxLevelCode listName="48">%(CustomerTaxLevelCode)s</cbc:TaxLevelCode>
            <cac:RegistrationAddress>
               <cbc:ID>%(CustomerCityCode)s</cbc:ID>
               <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(CustomerLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
               </cac:Country>
            </cac:RegistrationAddress>
            <cac:TaxScheme>
               <cbc:ID>%(TaxSchemeID)s</cbc:ID>
               <cbc:Name>%(TaxSchemeName)s</cbc:Name>
            </cac:TaxScheme>
         </cac:PartyTaxScheme>
         <cac:PartyLegalEntity>
            <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
        </cac:PartyLegalEntity>
        <cac:Contact>
           <cbc:ElectronicMail>%(CustomerElectronicMail)s</cbc:ElectronicMail>
        </cac:Contact>
        <cac:Person>
           <cbc:FirstName>%(Firstname)s</cbc:FirstName>
        </cac:Person>
      </cac:Party>
   </cac:AccountingCustomerParty>
   <cac:PaymentMeans>
      <cbc:ID>%(PaymentMeansID)s</cbc:ID>
      <cbc:PaymentMeansCode>%(PaymentMeansCode)s</cbc:PaymentMeansCode>
      <cbc:PaymentDueDate>%(PaymentDueDate)s</cbc:PaymentDueDate>
      <cbc:PaymentID>1234</cbc:PaymentID>      
   </cac:PaymentMeans>%(data_taxs_xml)s
   <cac:LegalMonetaryTotal>
      <cbc:LineExtensionAmount currencyID="%(CurrencyID)s">%(TotalLineExtensionAmount)s</cbc:LineExtensionAmount>
      <cbc:TaxExclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxExclusiveAmount)s</cbc:TaxExclusiveAmount>
      <cbc:TaxInclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxInclusiveAmount)s</cbc:TaxInclusiveAmount>
      <cbc:PayableAmount currencyID="%(CurrencyID)s">%(PayableAmount)s</cbc:PayableAmount>
   </cac:LegalMonetaryTotal>%(data_lines_xml)s
</Invoice>
"""
        return template_basic_data_contingencia_xml


    def _generate_data_contingencia_document_xml(self, template_basic_data_contingencia_xml, dc, dcd, data_taxs_xml, data_lines_xml, CUFE, data_xml_signature):
        template_basic_data_contingencia_xml = template_basic_data_contingencia_xml % {'InvoiceAuthorization' : dcd['InvoiceAuthorization'],
            'StartDate' : dcd['StartDate'],
            'EndDate' : dcd['EndDate'],
            'Prefix' : dcd['Prefix'],
            'From' : dcd['From'],
            'To' : dcd['To'],
            'IdentificationCode' : dc['IdentificationCode'],
            'ProviderID' : dc['ProviderID'],
            'SoftwareID' : dc['SoftwareID'],
            'SoftwareSecurityCode' : dc['SoftwareSecurityCode'],
            'UUID' : CUFE,            
            'UBLVersionID' : dc['UBLVersionID'],
            'CustomizationID' : dc['CustomizationID'],
            'ProfileID' : dc['ProfileID'], 
            'ProfileExecutionID' : dc['ProfileExecutionID'],                       
            'ContingencyID' : dcd['ContingencyID'],            
            'IssueDate' : dcd['IssueDate'],
            'IssueTime' : dcd['IssueTime'],
            'InvoiceTypeCode' : dcd['InvoiceTypeCode'],
            'DocumentCurrencyCode' : dcd['DocumentCurrencyCode'],
            'LineCountNumeric' : dcd['LineCountNumeric'],
            'SupplierAdditionalAccountID' : dc['SupplierAdditionalAccountID'],
            'SupplierPartyName' : dc['SupplierPartyName'],
            'SupplierCityCode' : dc['SupplierCityCode'],
            'SupplierCityName' : dc['SupplierCityName'],
            'SupplierCountrySubentity' : dc['SupplierCountrySubentity'],
            'SupplierCountrySubentityCode' : dc['SupplierCountrySubentityCode'],
            'SupplierLine' : dc['SupplierLine'],
            'SupplierCountryCode' : dc['SupplierCountryCode'],
            'SupplierCountryName' : dc['SupplierCountryName'],
            'schemeID' : dc['schemeID'],
            'SupplierTaxLevelCode' : dc['SupplierTaxLevelCode'],
            'TaxSchemeID' : dcd['TaxSchemeID'],
            'TaxSchemeName' : dcd['TaxSchemeName'],
            'SupplierElectronicMail' : dc['SupplierElectronicMail'],
            'CustomerAdditionalAccountID' : dcd['CustomerAdditionalAccountID'],
            'CustomerPartyName' : dcd['CustomerPartyName'],
            'CustomerschemeID' : dcd['CustomerschemeID'],
            'CustomerCityCode' : dcd['CustomerCityCode'],
            'CustomerCityName' : dcd['CustomerCityName'],
            'CustomerCountrySubentity' : dcd['CustomerCountrySubentity'],
            'CustomerCountrySubentityCode' : dcd['CustomerCountrySubentityCode'],
            'CustomerLine' : dcd['CustomerLine'],
            'CustomerCountryCode' : dcd['CustomerCountryCode'],            
            'CustomerCountryName' : dcd['CustomerCountryName'],
            'CustomerSchemeID' : dcd['CustomerSchemeID'],
            'CustomerID' : dcd['CustomerID'],
            'CustomerTaxLevelCode' : dcd['CustomerTaxLevelCode'],
            'CustomerElectronicMail' : dcd['CustomerElectronicMail'],
            'Firstname' : dcd['Firstname'],
            'PaymentMeansID' : dcd['PaymentMeansID'], 
            'PaymentMeansCode' : dcd['PaymentMeansCode'], 
            'PaymentDueDate' : dcd['PaymentDueDate'],
            'data_taxs_xml' : data_taxs_xml,
            'TotalLineExtensionAmount' : dcd['LineExtensionAmount'],
            'TotalTaxExclusiveAmount' : dcd['TaxExclusiveAmount'],
            'TotalTaxInclusiveAmount' : dcd['TotalTaxInclusiveAmount'],
            'PayableAmount' : dcd['PayableAmount'], 
            'data_lines_xml' : data_lines_xml,
            'ContingencyReferenceID' : dcd['ContingencyReferenceID'],  
            'ContingencyDocumentTypeCode' : dcd['ContingencyDocumentTypeCode'],
            'ContingencyIssueDate' : dcd['ContingencyIssueDate'],
            'CurrencyID' : dcd['CurrencyID'],
            'SchemeIDAdquiriente' : dcd['SchemeIDAdquiriente'],
            'SchemeNameAdquiriente' : dcd['SchemeNameAdquiriente'],
            'IDAdquiriente' : dcd['IDAdquiriente']
            }
        return template_basic_data_contingencia_xml


    def _template_basic_data_nc_xml(self):
        template_basic_data_nc_xml = """
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2    http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-CreditNote-2.1.xsd">
    <ext:UBLExtensions>
        <ext:UBLExtension>
            <ext:ExtensionContent>
                <sts:DianExtensions>
                    <sts:InvoiceSource>
                        <cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1">%(IdentificationCode)s</cbc:IdentificationCode>
                    </sts:InvoiceSource>
                    <sts:SoftwareProvider>
                        <sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</sts:ProviderID>
                        <sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareID)s</sts:SoftwareID>
                    </sts:SoftwareProvider>
                    <sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareSecurityCode)s</sts:SoftwareSecurityCode>
                    <sts:AuthorizationProvider>
                        <sts:AuthorizationProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="4" schemeName="31">800197268</sts:AuthorizationProviderID>
                    </sts:AuthorizationProvider>
                    <sts:QRCode>URL=https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentKey=%(UUID)s</sts:QRCode>
                </sts:DianExtensions>
            </ext:ExtensionContent>
        </ext:UBLExtension>   
        <ext:UBLExtension>
            <ext:ExtensionContent></ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>
    
    <cbc:DiscrepancyResponse>
        <cbc:ResponseCode>%(ResponseCodeCreditNote)s</cbc:ResponseCode>
        <cbc:Description>%(DescriptionCreditNote)s</cbc:Description>        
    </cbc:DiscrepancyResponse>
    
    <cbc:UBLVersionID>%(UBLVersionID)s</cbc:UBLVersionID>
    <cbc:CustomizationID>%(CustomizationID)s</cbc:CustomizationID>
    <cbc:ProfileID>%(ProfileID)s</cbc:ProfileID>
    <cbc:ProfileExecutionID>%(ProfileExecutionID)s</cbc:ProfileExecutionID>
    <cbc:ID>%(InvoiceID)s</cbc:ID>
    <cbc:UUID schemeID="%(ProfileExecutionID)s" schemeName="CUDE-SHA384">%(UUID)s</cbc:UUID>
    <cbc:IssueDate>%(IssueDate)s</cbc:IssueDate>
    <cbc:IssueTime>%(IssueTime)s</cbc:IssueTime>
    <cbc:CreditNoteTypeCode>%(CreditNoteTypeCode)s</cbc:CreditNoteTypeCode>
    <cbc:DocumentCurrencyCode>%(DocumentCurrencyCode)s</cbc:DocumentCurrencyCode>
    <cbc:LineCountNumeric>%(LineCountNumeric)s</cbc:LineCountNumeric>
    <cac:BillingReference>
       <cac:InvoiceDocumentReference>
          <cbc:ID>%(InvoiceReferenceID)s</cbc:ID>
          <cbc:UUID schemeName="CUFE-SHA384">%(InvoiceReferenceUUID)s</cbc:UUID>
          <cbc:IssueDate>%(InvoiceReferenceDate)s</cbc:IssueDate>
       </cac:InvoiceDocumentReference>
    </cac:BillingReference>
    <cac:AccountingSupplierParty>
      <cbc:AdditionalAccountID>%(SupplierAdditionalAccountID)s</cbc:AdditionalAccountID>
      <cac:Party>
         <cac:PartyName>
            <cbc:Name>%(SupplierPartyName)s</cbc:Name>
         </cac:PartyName>
         <cac:PhysicalLocation>
            <cac:Address>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:Address>
         </cac:PhysicalLocation>
         <cac:PartyTaxScheme>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cbc:TaxLevelCode listName="48">%(SupplierTaxLevelCode)s</cbc:TaxLevelCode>
            <cac:RegistrationAddress>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:RegistrationAddress>
            <cac:TaxScheme>
               <cbc:ID>%(TaxSchemeID)s</cbc:ID>
               <cbc:Name>%(TaxSchemeName)s</cbc:Name>
            </cac:TaxScheme>
         </cac:PartyTaxScheme>
         <cac:PartyLegalEntity>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cac:CorporateRegistrationScheme>
               <cbc:ID>%(Prefix)s</cbc:ID>
            </cac:CorporateRegistrationScheme>
         </cac:PartyLegalEntity>
         <cac:Contact>
           <cbc:ElectronicMail>%(SupplierElectronicMail)s</cbc:ElectronicMail>
         </cac:Contact>   
      </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
       <cbc:AdditionalAccountID>%(CustomerAdditionalAccountID)s</cbc:AdditionalAccountID>
       <cac:Party>
          <cac:PartyIdentification>
             <cbc:ID schemeName="%(SchemeNameAdquiriente)s" schemeID="%(SchemeIDAdquiriente)s">%(IDAdquiriente)s</cbc:ID>                        
          </cac:PartyIdentification>
          <cac:PartyName>
             <cbc:Name>%(CustomerPartyName)s</cbc:Name>
          </cac:PartyName>
          <cac:PhysicalLocation>
             <cac:Address>
                <cbc:ID>%(CustomerCityCode)s</cbc:ID>
                <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
                <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
                <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
                <cac:AddressLine>
                   <cbc:Line>%(CustomerLine)s</cbc:Line>
                </cac:AddressLine>
                <cac:Country>
                   <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                   <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
                </cac:Country>
             </cac:Address>
          </cac:PhysicalLocation>
          <cac:PartyTaxScheme>
             <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
             <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
             <cbc:TaxLevelCode listName="48">%(CustomerTaxLevelCode)s</cbc:TaxLevelCode>
             <cac:RegistrationAddress>
                <cbc:ID>%(CustomerCityCode)s</cbc:ID>
                <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
                <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
                <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
                <cac:AddressLine>
                   <cbc:Line>%(CustomerLine)s</cbc:Line>
                </cac:AddressLine>
                <cac:Country>
                   <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                   <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
                </cac:Country>
             </cac:RegistrationAddress>
             <cac:TaxScheme>
                <cbc:ID>%(TaxSchemeID)s</cbc:ID>
                <cbc:Name>%(TaxSchemeName)s</cbc:Name>
             </cac:TaxScheme>
          </cac:PartyTaxScheme>
          <cac:PartyLegalEntity>
             <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
             <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
         </cac:PartyLegalEntity>
         <cac:Contact>
            <cbc:ElectronicMail>%(CustomerElectronicMail)s</cbc:ElectronicMail>
         </cac:Contact>
         <cac:Person>
            <cbc:FirstName>%(Firstname)s</cbc:FirstName>
         </cac:Person>
       </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:PaymentMeans>
       <cbc:ID>%(PaymentMeansID)s</cbc:ID>
       <cbc:PaymentMeansCode>%(PaymentMeansCode)s</cbc:PaymentMeansCode>
       <cbc:PaymentDueDate>%(PaymentDueDate)s</cbc:PaymentDueDate>
       <cbc:PaymentID>1234</cbc:PaymentID>      
    </cac:PaymentMeans>%(data_taxs_xml)s
    <cac:LegalMonetaryTotal>
       <cbc:LineExtensionAmount currencyID="%(CurrencyID)s">%(TotalLineExtensionAmount)s</cbc:LineExtensionAmount>
       <cbc:TaxExclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxExclusiveAmount)s</cbc:TaxExclusiveAmount>
       <cbc:TaxInclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxInclusiveAmount)s</cbc:TaxInclusiveAmount>
       <cbc:PayableAmount currencyID="%(CurrencyID)s">%(PayableAmount)s</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>%(data_credit_lines_xml)s
    
</CreditNote>"""
        return template_basic_data_nc_xml


    def _generate_data_nc_document_xml(self, template_basic_data_nc_xml, dc, dcd, data_credit_lines_xml, CUFE, data_taxs_xml):
        template_basic_data_nc_xml = template_basic_data_nc_xml % {'InvoiceAuthorization' : dcd['InvoiceAuthorization'],
            'StartDate' : dcd['StartDate'],
            'EndDate' : dcd['EndDate'],
            'Prefix' : dcd['Prefix'],
            'From' : dcd['From'],
            'To' : dcd['To'],
            'IdentificationCode' : dc['IdentificationCode'],
            'ProviderID' : dc['ProviderID'],
            'SoftwareID' : dc['SoftwareID'],
            'SoftwareSecurityCode' : dc['SoftwareSecurityCode'],
            'PayableAmount' : dcd['PayableAmount'],
            'UBLVersionID' : dc['UBLVersionID'],
            'ProfileExecutionID' : dc['ProfileExecutionID'],
            'ProfileID' : dc['ProfileID'],
            'CustomizationID' : dc['CustomizationID'],
            'InvoiceID' : dcd['InvoiceID'],
            'UUID' : CUFE,
            'IssueDate' : dcd['IssueDate'],
            'IssueTime' : dcd['IssueTime'],
            'CreditNoteTypeCode' : dcd['CreditNoteTypeCode'],
            'LineCountNumeric' : dcd['LineCountNumeric'],
            'TaxSchemeID' : dcd['TaxSchemeID'],
            'TaxSchemeName' : dcd['TaxSchemeName'],
            'DocumentCurrencyCode' : dcd['DocumentCurrencyCode'],
            'SupplierAdditionalAccountID' : dc['SupplierAdditionalAccountID'],
            'SupplierPartyName' : dc['SupplierPartyName'],
            'SupplierCountrySubentityCode' : dc['SupplierCountrySubentityCode'],
            'SupplierCityName' : dc['SupplierCityName'],
            'SupplierCountrySubentity' : dc['SupplierCountrySubentity'],
            'SupplierLine' : dc['SupplierLine'],
            'SupplierCountryCode' : dc['SupplierCountryCode'],
            'SupplierCountryName' : dc['SupplierCountryName'],
            'SupplierTaxLevelCode' : dc['SupplierTaxLevelCode'],
            'SupplierCityCode' : dc['SupplierCityCode'],
            'SupplierElectronicMail' : dc['SupplierElectronicMail'],
            'schemeID' : dc['schemeID'],
            'CustomerAdditionalAccountID' : dcd['CustomerAdditionalAccountID'],
            'CustomerID' : dcd['CustomerID'],
            'CustomerSchemeID' : dcd['CustomerSchemeID'],
            'CustomerPartyName' : dcd['CustomerPartyName'],
            'CustomerCountrySubentityCode' : dcd['CustomerCountrySubentityCode'],
            'CustomerCountrySubentity' : dcd['CustomerCountrySubentity'],
            'CustomerCityName' : dcd['CustomerCityName'],
            'CustomerLine' : dcd['CustomerLine'],
            'CustomerCountryCode' : dcd['CustomerCountryCode'],
            'CustomerCountryName' : dcd['CustomerCountryName'],
            'CustomerTaxLevelCode' : dcd['CustomerTaxLevelCode'],
            'CustomerschemeID' : dcd['CustomerschemeID'],
            'CustomerCityCode' : dcd['CustomerCityCode'],
            'CustomerElectronicMail' : dcd['CustomerElectronicMail'],
            'TotalLineExtensionAmount' : dcd['LineExtensionAmount'],
            'TotalTaxExclusiveAmount' : dcd['TaxExclusiveAmount'],
            'PaymentMeansID' : dcd['PaymentMeansID'], 
            'PaymentMeansCode' : dcd['PaymentMeansCode'],  
            'PaymentDueDate' : dcd['PaymentDueDate'],
            'TotalTaxInclusiveAmount' : dcd['TotalTaxInclusiveAmount'],
            'Firstname' : dcd['Firstname'],
            'InvoiceReferenceID' : dcd['InvoiceReferenceID'],
            'InvoiceReferenceUUID' : dcd['InvoiceReferenceUUID'],
            'InvoiceReferenceDate' : dcd['InvoiceReferenceDate'],
            'data_taxs_xml' : data_taxs_xml,
            'data_credit_lines_xml' : data_credit_lines_xml,
            'CurrencyID' : dcd['CurrencyID'],
            'SchemeIDAdquiriente' : dcd['SchemeIDAdquiriente'],
            'SchemeNameAdquiriente' : dcd['SchemeNameAdquiriente'],
            'IDAdquiriente' : dcd['IDAdquiriente'],
            'ResponseCodeCreditNote' : dcd['ResponseCodeCreditNote'],
            'DescriptionCreditNote': dcd['DescriptionDebitCreditNote'],
            'SupplierCityNameSubentity': dc['SupplierCityNameSubentity'],
            'DeliveryAddress': dc['DeliveryAddress'],
            }
        return template_basic_data_nc_xml

 
    def _template_basic_data_nd_xml(self):
        template_basic_data_nd_xml = """
<DebitNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2    http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-DebitNote-2.1.xsd">
   <ext:UBLExtensions>
        <ext:UBLExtension>
            <ext:ExtensionContent>
                <sts:DianExtensions>
                    <sts:InvoiceSource>
                        <cbc:IdentificationCode listAgencyID="6" listAgencyName="United Nations Economic Commission for Europe" listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1">%(IdentificationCode)s</cbc:IdentificationCode>
                    </sts:InvoiceSource>
                    <sts:SoftwareProvider>
                        <sts:ProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</sts:ProviderID>
                        <sts:SoftwareID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareID)s</sts:SoftwareID>
                    </sts:SoftwareProvider>
                    <sts:SoftwareSecurityCode schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">%(SoftwareSecurityCode)s</sts:SoftwareSecurityCode>
                    <sts:AuthorizationProvider>
                        <sts:AuthorizationProviderID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="4" schemeName="31">800197268</sts:AuthorizationProviderID>
                    </sts:AuthorizationProvider>
                    <sts:QRCode>URL=https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentKey=%(UUID)s</sts:QRCode>
                </sts:DianExtensions>
            </ext:ExtensionContent>
        </ext:UBLExtension>   
        <ext:UBLExtension>
            <ext:ExtensionContent></ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>
    
    <cbc:DiscrepancyResponse>
        <cbc:ResponseCode>%(ResponseCodeDebitNote)s</cbc:ResponseCode>
        <cbc:Description>%(DescriptionDebitNote)s</cbc:Description>        
    </cbc:DiscrepancyResponse>
    
    <cbc:UBLVersionID>%(UBLVersionID)s</cbc:UBLVersionID>
    <cbc:CustomizationID>%(CustomizationID)s</cbc:CustomizationID>
    <cbc:ProfileID>%(ProfileID)s</cbc:ProfileID>
    <cbc:ProfileExecutionID>%(ProfileExecutionID)s</cbc:ProfileExecutionID>
    <cbc:ID>%(InvoiceID)s</cbc:ID>
    <cbc:UUID schemeID="%(ProfileExecutionID)s" schemeName="CUDE-SHA384">%(UUID)s</cbc:UUID>
    <cbc:IssueDate>%(IssueDate)s</cbc:IssueDate>
    <cbc:IssueTime>%(IssueTime)s</cbc:IssueTime>
    <cbc:DocumentCurrencyCode>%(DocumentCurrencyCode)s</cbc:DocumentCurrencyCode>
    <cbc:LineCountNumeric>%(LineCountNumeric)s</cbc:LineCountNumeric>
    <cac:BillingReference>
       <cac:InvoiceDocumentReference>
          <cbc:ID>%(InvoiceReferenceID)s</cbc:ID>
          <cbc:UUID schemeName="CUFE-SHA384">%(InvoiceReferenceUUID)s</cbc:UUID>
          <cbc:IssueDate>%(InvoiceReferenceDate)s</cbc:IssueDate>
       </cac:InvoiceDocumentReference>
    </cac:BillingReference>
    <cac:AccountingSupplierParty>
      <cbc:AdditionalAccountID>%(SupplierAdditionalAccountID)s</cbc:AdditionalAccountID>
      <cac:Party>
         <cac:PartyName>
            <cbc:Name>%(SupplierPartyName)s</cbc:Name>
         </cac:PartyName>
         <cac:PhysicalLocation>
            <cac:Address>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:Address>
         </cac:PhysicalLocation>
         <cac:PartyTaxScheme>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cbc:TaxLevelCode listName="48">%(SupplierTaxLevelCode)s</cbc:TaxLevelCode>
            <cac:RegistrationAddress>
               <cbc:ID>%(SupplierCityCode)s</cbc:ID>
               <cbc:CityName>%(SupplierCityName)s</cbc:CityName>
               <cbc:CountrySubentity>%(SupplierCountrySubentity)s</cbc:CountrySubentity>
               <cbc:CountrySubentityCode>%(SupplierCountrySubentityCode)s</cbc:CountrySubentityCode>
               <cac:AddressLine>
                  <cbc:Line>%(SupplierLine)s</cbc:Line>
               </cac:AddressLine>
               <cac:Country>
                  <cbc:IdentificationCode>%(SupplierCountryCode)s</cbc:IdentificationCode>
                  <cbc:Name languageID="es">%(SupplierCountryName)s</cbc:Name>
               </cac:Country>
            </cac:RegistrationAddress>
            <cac:TaxScheme>
               <cbc:ID>%(TaxSchemeID)s</cbc:ID>
               <cbc:Name>%(TaxSchemeName)s</cbc:Name>
            </cac:TaxScheme>
         </cac:PartyTaxScheme>
         <cac:PartyLegalEntity>
            <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
            <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(schemeID)s" schemeName="31">%(ProviderID)s</cbc:CompanyID>
            <cac:CorporateRegistrationScheme>
               <cbc:ID>%(Prefix)s</cbc:ID>
            </cac:CorporateRegistrationScheme>
         </cac:PartyLegalEntity>
         <cac:Contact>
           <cbc:ElectronicMail>%(SupplierElectronicMail)s</cbc:ElectronicMail>
         </cac:Contact>   
      </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
       <cbc:AdditionalAccountID>%(CustomerAdditionalAccountID)s</cbc:AdditionalAccountID>
       <cac:Party>
          <cac:PartyIdentification>
             <cbc:ID schemeName="%(SchemeNameAdquiriente)s" schemeID="%(SchemeIDAdquiriente)s">%(IDAdquiriente)s</cbc:ID>                        
          </cac:PartyIdentification>
          <cac:PartyName>
             <cbc:Name>%(CustomerPartyName)s</cbc:Name>
          </cac:PartyName>
          <cac:PhysicalLocation>
             <cac:Address>
                <cbc:ID>%(CustomerCityCode)s</cbc:ID>
                <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
                <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
                <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
                <cac:AddressLine>
                   <cbc:Line>%(CustomerLine)s</cbc:Line>
                </cac:AddressLine>
                <cac:Country>
                   <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                   <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
                </cac:Country>
             </cac:Address>
          </cac:PhysicalLocation>
          <cac:PartyTaxScheme>
             <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
             <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
             <cbc:TaxLevelCode listName="48">%(CustomerTaxLevelCode)s</cbc:TaxLevelCode>
             <cac:RegistrationAddress>
                <cbc:ID>%(CustomerCityCode)s</cbc:ID>
                <cbc:CityName>%(CustomerCityName)s</cbc:CityName>
                <cbc:CountrySubentity>%(CustomerCountrySubentity)s</cbc:CountrySubentity>
                <cbc:CountrySubentityCode>%(CustomerCountrySubentityCode)s</cbc:CountrySubentityCode>
                <cac:AddressLine>
                   <cbc:Line>%(CustomerLine)s</cbc:Line>
                </cac:AddressLine>
                <cac:Country>
                   <cbc:IdentificationCode>%(CustomerCountryCode)s</cbc:IdentificationCode>
                   <cbc:Name languageID="es">%(CustomerCountryName)s</cbc:Name>
                </cac:Country>
             </cac:RegistrationAddress>
             <cac:TaxScheme>
                <cbc:ID>%(TaxSchemeID)s</cbc:ID>
                <cbc:Name>%(TaxSchemeName)s</cbc:Name>
             </cac:TaxScheme>
          </cac:PartyTaxScheme>
          <cac:PartyLegalEntity>
             <cbc:RegistrationName>%(CustomerPartyName)s</cbc:RegistrationName>
             <cbc:CompanyID schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeID="%(CustomerschemeID)s" schemeName="31">%(CustomerID)s</cbc:CompanyID>
         </cac:PartyLegalEntity>
         <cac:Contact>
            <cbc:ElectronicMail>%(CustomerElectronicMail)s</cbc:ElectronicMail>
         </cac:Contact>
         <cac:Person>
            <cbc:FirstName>%(Firstname)s</cbc:FirstName>
         </cac:Person>
       </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:PaymentMeans>
       <cbc:ID>%(PaymentMeansID)s</cbc:ID>
       <cbc:PaymentMeansCode>%(PaymentMeansCode)s</cbc:PaymentMeansCode>
       <cbc:PaymentDueDate>%(PaymentDueDate)s</cbc:PaymentDueDate>
       <cbc:PaymentID>1234</cbc:PaymentID>      
    </cac:PaymentMeans>%(data_taxs_xml)s
    <cac:RequestedMonetaryTotal>
       <cbc:LineExtensionAmount currencyID="%(CurrencyID)s">%(TotalLineExtensionAmount)s</cbc:LineExtensionAmount>
       <cbc:TaxExclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxExclusiveAmount)s</cbc:TaxExclusiveAmount>
       <cbc:TaxInclusiveAmount currencyID="%(CurrencyID)s">%(TotalTaxInclusiveAmount)s</cbc:TaxInclusiveAmount>
       <cbc:PayableAmount currencyID="%(CurrencyID)s">%(PayableAmount)s</cbc:PayableAmount>
    </cac:RequestedMonetaryTotal>%(data_debit_lines_xml)s
   
</DebitNote>"""
        return template_basic_data_nd_xml


    def _generate_data_nd_document_xml(self, template_basic_data_nc_xml, dc, dcd, data_debit_lines_xml, CUFE, data_taxs_xml):
        template_basic_data_nd_xml = template_basic_data_nc_xml % {'InvoiceAuthorization' : dcd['InvoiceAuthorization'],
            'StartDate' : dcd['StartDate'],
            'EndDate' : dcd['EndDate'],
            'Prefix' : dcd['Prefix'],
            'From' : dcd['From'],
            'To' : dcd['To'],
            'IdentificationCode' : dc['IdentificationCode'],
            'ProviderID' : dc['ProviderID'],
            'SoftwareID' : dc['SoftwareID'],
            'SoftwareSecurityCode' : dc['SoftwareSecurityCode'],
            'PayableAmount' : dcd['PayableAmount'],
            'UBLVersionID' : dc['UBLVersionID'],
            'ProfileExecutionID' : dc['ProfileExecutionID'],
            'ProfileID' : dc['ProfileID'],
            'CustomizationID' : dc['CustomizationID'],
            'InvoiceID' : dcd['InvoiceID'],
            'UUID' : CUFE,
            'IssueDate' : dcd['IssueDate'],
            'IssueTime' : dcd['IssueTime'],
            'DebitNoteTypeCode' : dcd['DebitNoteTypeCode'],
            'LineCountNumeric' : dcd['LineCountNumeric'],
            'TaxSchemeID' : dcd['TaxSchemeID'],
            'TaxSchemeName' : dcd['TaxSchemeName'],
            'DocumentCurrencyCode' : dcd['DocumentCurrencyCode'],
            'SupplierAdditionalAccountID' : dc['SupplierAdditionalAccountID'],
            'SupplierPartyName' : dc['SupplierPartyName'],
            'SupplierCountrySubentityCode' : dc['SupplierCountrySubentityCode'],
            'SupplierCityName' : dc['SupplierCityName'],
            'SupplierCountrySubentity' : dc['SupplierCountrySubentity'],
            'SupplierLine' : dc['SupplierLine'],
            'SupplierCountryCode' : dc['SupplierCountryCode'],
            'SupplierCountryName' : dc['SupplierCountryName'],
            'SupplierTaxLevelCode' : dc['SupplierTaxLevelCode'],
            'SupplierCityCode' : dc['SupplierCityCode'],
            'SupplierElectronicMail' : dc['SupplierElectronicMail'],
            'schemeID' : dc['schemeID'],
            'CustomerAdditionalAccountID' : dcd['CustomerAdditionalAccountID'],
            'CustomerID' : dcd['CustomerID'],
            'CustomerSchemeID' : dcd['CustomerSchemeID'],
            'CustomerPartyName' : dcd['CustomerPartyName'],
            'CustomerCountrySubentityCode' : dcd['CustomerCountrySubentityCode'],
            'CustomerCountrySubentity' : dcd['CustomerCountrySubentity'],
            'CustomerCityName' : dcd['CustomerCityName'],
            'CustomerLine' : dcd['CustomerLine'],
            'CustomerCountryCode' : dcd['CustomerCountryCode'],
            'CustomerCountryName' : dcd['CustomerCountryName'],
            'CustomerTaxLevelCode' : dcd['CustomerTaxLevelCode'],
            'CustomerschemeID' : dcd['CustomerschemeID'],
            'CustomerCityCode' : dcd['CustomerCityCode'],
            'CustomerElectronicMail' : dcd['CustomerElectronicMail'],
            'TotalLineExtensionAmount' : dcd['LineExtensionAmount'],
            'TotalTaxExclusiveAmount' : dcd['TaxExclusiveAmount'],
            'PaymentMeansID' : dcd['PaymentMeansID'], 
            'PaymentMeansCode' : dcd['PaymentMeansCode'],  
            'PaymentDueDate' : dcd['PaymentDueDate'],
            'TotalTaxInclusiveAmount' : dcd['TotalTaxInclusiveAmount'],
            'Firstname' : dcd['Firstname'],
            'InvoiceReferenceID' : dcd['InvoiceReferenceID'],
            'InvoiceReferenceUUID' : dcd['InvoiceReferenceUUID'],
            'InvoiceReferenceDate' : dcd['InvoiceReferenceDate'],
            'data_taxs_xml' : data_taxs_xml,
            'data_debit_lines_xml' : data_debit_lines_xml,
            'CurrencyID' : dcd['CurrencyID'],
            'SchemeIDAdquiriente' : dcd['SchemeIDAdquiriente'],
            'SchemeNameAdquiriente' : dcd['SchemeNameAdquiriente'],
            'IDAdquiriente' : dcd['IDAdquiriente'],
            'ResponseCode': dcd['ResponseCodeDebitNote'],
            'Description': dcd['DescriptionDebitCreditNote'],
            'SupplierCityNameSubentity': dc['SupplierCityNameSubentity'],
            'DeliveryAddress': dc['DeliveryAddress'],
            }
        return template_basic_data_nd_xml


    def _template_tax_data_xml(self):
        template_tax_data_xml = """
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="%(CurrencyID)s">%(TaxTotalTaxableAmount)s</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="%(CurrencyID)s">%(TaxTotalTaxAmount)s</cbc:TaxAmount>
            <cbc:Percent>%(TaxTotalPercent)s</cbc:Percent>
            <cac:TaxCategory>
                <cbc:Percent>%(TaxTotalPercent)s</cbc:Percent>
                <cac:TaxScheme>
                    <cbc:ID>%(TaxTotalTaxSchemeID)s</cbc:ID>
                    <cbc:Name>%(TaxTotalName)s</cbc:Name>
                </cac:TaxScheme>
            </cac:TaxCategory>
        </cac:TaxSubtotal>"""
        return template_tax_data_xml

    def _template_line_data_information_content_provider_party_xml(self):
        return """
            <cac:InformationContentProviderParty>
                <cac:PowerOfAttorney>
                    <cac:AgentParty>
                        <cac:PartyIdentification>
                            <cbc:ID schemeAgencyID="195" schemeID="3" schemeName="31">%(MandanteNumberIdentification)s</cbc:ID>
                        </cac:PartyIdentification>
                    </cac:AgentParty>
                </cac:PowerOfAttorney>
            </cac:InformationContentProviderParty>
        """

    def _template_line_data_xml(self):
        template_line_data_xml = """
    <cac:InvoiceLine>
        <cbc:ID>%(ILLinea)s</cbc:ID>
        <cbc:InvoicedQuantity unitCode="EA">%(ILInvoicedQuantity)s</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="%(CurrencyID)s">%(ILLineExtensionAmount)s</cbc:LineExtensionAmount>
        <cbc:FreeOfChargeIndicator>false</cbc:FreeOfChargeIndicator>
        <cac:TaxTotal>
           
           <cbc:TaxAmount currencyID="%(CurrencyID)s">%(ILTaxAmount)s</cbc:TaxAmount>%(InvoiceLineTaxSubtotal)s
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Description>%(ILDescription)s</cbc:Description>
            <cac:StandardItemIdentification>
              <cbc:ID schemeAgencyID="10" schemeID="001" schemeName="UNSPSC">%(ID_UNSPSC)s</cbc:ID>
            </cac:StandardItemIdentification>
            %(InformationContentProviderParty)s
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="%(CurrencyID)s">%(ILPriceAmount)s</cbc:PriceAmount>
            <cbc:BaseQuantity unitCode="NIU">1.0000</cbc:BaseQuantity>
        </cac:Price>
    </cac:InvoiceLine>""" 
        return template_line_data_xml


    def _template_InvoiceLineTaxSubtotal_xml(self):
        template_InvoiceLineTaxSubtotal_xml = """
           <cac:TaxSubtotal>
              <cbc:TaxableAmount currencyID="%(CurrencyID)s">%(ILTaxableAmount)s</cbc:TaxableAmount>
              <cbc:TaxAmount currencyID="%(CurrencyID)s">%(ILTaxAmountSubtotal)s</cbc:TaxAmount>
              <cac:TaxCategory>
                 <cbc:Percent>%(ILPercent)s</cbc:Percent>
                 <cac:TaxScheme>
                    <cbc:ID>%(ILID)s</cbc:ID>
                    <cbc:Name>%(ILName)s</cbc:Name>
                 </cac:TaxScheme>
              </cac:TaxCategory>
           </cac:TaxSubtotal>"""
        return template_InvoiceLineTaxSubtotal_xml


    def _template_credit_line_data_xml(self):
        template_credit_line_data_xml = """
    <cac:CreditNoteLine>
        <cbc:ID>%(ILLinea)s</cbc:ID>
        <cbc:CreditedQuantity unitCode="EA">%(ILInvoicedQuantity)s</cbc:CreditedQuantity>
        <cbc:LineExtensionAmount currencyID="%(CurrencyID)s">%(ILLineExtensionAmount)s</cbc:LineExtensionAmount>
        <cbc:FreeOfChargeIndicator>false</cbc:FreeOfChargeIndicator>
        <cac:TaxTotal>
           
           <cbc:TaxAmount currencyID="%(CurrencyID)s">%(ILTaxAmount)s</cbc:TaxAmount>
           <cbc:RoundingAmount currencyID="%(CurrencyID)s">%(TaxRoundingAmount)s</cbc:RoundingAmount>
           <cac:TaxSubtotal>
              <cbc:TaxableAmount currencyID="%(CurrencyID)s">%(ILTaxableAmount)s</cbc:TaxableAmount>
              <cbc:TaxAmount currencyID="%(CurrencyID)s">%(ILTaxAmount)s</cbc:TaxAmount>
              <cac:TaxCategory>
                 <cbc:Percent>%(ILPercent)s</cbc:Percent>
                 <cac:TaxScheme>
                    <cbc:ID>%(ILID)s</cbc:ID>
                    <cbc:Name>%(ILName)s</cbc:Name>
                 </cac:TaxScheme>
              </cac:TaxCategory>
           </cac:TaxSubtotal>
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Description>%(ILDescription)s</cbc:Description>
            <cac:StandardItemIdentification>
              <cbc:ID schemeAgencyID="10" schemeID="001" schemeName="UNSPSC">%(ID_UNSPSC)s</cbc:ID>
            </cac:StandardItemIdentification>
            %(InformationContentProviderParty)s
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="%(CurrencyID)s">%(ILPriceAmount)s</cbc:PriceAmount>
            <cbc:BaseQuantity unitCode="NIU">1.0000</cbc:BaseQuantity>
        </cac:Price>
    </cac:CreditNoteLine>""" 
        return template_credit_line_data_xml


    def _template_debit_line_data_xml(self):
        template_debit_line_data_xml = """
    <cac:DebitNoteLine>
        <cbc:ID>%(ILLinea)s</cbc:ID>
        <cbc:DebitedQuantity unitCode="EA">%(ILInvoicedQuantity)s</cbc:DebitedQuantity>
        <cbc:LineExtensionAmount currencyID="%(CurrencyID)s">%(ILLineExtensionAmount)s</cbc:LineExtensionAmount>
        <cac:TaxTotal>
           
           <cbc:TaxAmount currencyID="%(CurrencyID)s">%(ILTaxAmount)s</cbc:TaxAmount>
           <cac:TaxSubtotal>
              <cbc:TaxableAmount currencyID="%(CurrencyID)s">%(ILTaxableAmount)s</cbc:TaxableAmount>
              <cbc:TaxAmount currencyID="%(CurrencyID)s">%(ILTaxAmount)s</cbc:TaxAmount>
              <cac:TaxCategory>
                 <cbc:Percent>%(ILPercent)s</cbc:Percent>
                 <cac:TaxScheme>
                    <cbc:ID>%(ILID)s</cbc:ID>
                    <cbc:Name>%(ILName)s</cbc:Name>
                 </cac:TaxScheme>
              </cac:TaxCategory>
           </cac:TaxSubtotal>
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Description>%(ILDescription)s</cbc:Description>
            <cac:StandardItemIdentification>
              <cbc:ID schemeAgencyID="10" schemeID="001" schemeName="UNSPSC">%(ID_UNSPSC)s</cbc:ID>
            </cac:StandardItemIdentification>
            %(InformationContentProviderParty)s
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="%(CurrencyID)s">%(ILPriceAmount)s</cbc:PriceAmount>
            <cbc:BaseQuantity unitCode="NIU">1.0000</cbc:BaseQuantity>
        </cac:Price>
    </cac:DebitNoteLine>""" 
        return template_debit_line_data_xml


    def _template_signature_data_xml(self):
        template_signature_data_xml = """                               
                <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-%(identifier)s">
                    <ds:SignedInfo>
                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                        <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                        <ds:Reference Id="xmldsig-%(identifier)s-ref0" URI="">
                            <ds:Transforms>
                                <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                            </ds:Transforms>
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>                                             
                            <ds:DigestValue>%(data_xml_signature_ref_zero)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference URI="#xmldsig-%(identifierkeyinfo)s-keyinfo">
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                            <ds:DigestValue>%(data_xml_keyinfo_base)s</ds:DigestValue>
                        </ds:Reference>
                        <ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-%(identifier)s-signedprops">
                            <ds:DigestMethod  Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                            <ds:DigestValue>%(data_xml_SignedProperties_base)s</ds:DigestValue>
                        </ds:Reference>
                    </ds:SignedInfo>
                    <ds:SignatureValue Id="xmldsig-%(identifier)s-sigvalue">%(SignatureValue)s</ds:SignatureValue>
                    <ds:KeyInfo Id="xmldsig-%(identifierkeyinfo)s-keyinfo">
                        <ds:X509Data>
                            <ds:X509Certificate>%(data_public_certificate_base)s</ds:X509Certificate>
                        </ds:X509Data>
                    </ds:KeyInfo>
                    <ds:Object>
                        <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#xmldsig-%(identifier)s">
                            <xades:SignedProperties Id="xmldsig-%(identifier)s-signedprops">
                                <xades:SignedSignatureProperties>
                                    <xades:SigningTime>%(data_xml_SigningTime)s</xades:SigningTime>
                                    <xades:SigningCertificate>
                                        <xades:Cert>
                                            <xades:CertDigest>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
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
                                                <xades:Description>Politica de firma para facturas electronicas de la Republica de Colombia</xades:Description>
                                            </xades:SigPolicyId>
                                            <xades:SigPolicyHash>
                                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
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


    @api.model
    def _get_taxs_data(self, invoice_id):
        dic_taxs_data = {}
        company = self.env.user.company_id
        partner = company.partner_id
        iva_lines = 1
        ret_lines = 1
        iva_01 = 0.00
        ica_03 = 0.00
        inc_04 = 0.00
        ret_06 = 0.00
        tax_percentage_iva_01 = 0.00
        tax_percentage_ica_03 = 0.00
        tax_percentage_inc_04 = 0.00
        tax_percentage_ret_06 = 0.00
        total_base_iva_01 = 0.00
        total_base_ica_03 = 0.00
        total_base_inc_04 = 0.00
        total_base_ret_06 = 0.00
        data_tax_detail_doc = self.env['account.invoice.tax'].search([('invoice_id', '=', invoice_id)])

        if data_tax_detail_doc:
            for item_tax in data_tax_detail_doc:
                iva_01 += item_tax.amount if item_tax.tax_id.tax_group_fe == 'iva_fe' else 0.0
                ica_03 += item_tax.amount if item_tax.tax_id.tax_group_fe == 'ica_fe' else 0.0
                inc_04 += item_tax.amount if item_tax.tax_id.tax_group_fe == 'ico_fe' else 0.0 # Mod impuesto
                ret_06 = item_tax.amount if item_tax.tax_id.tax_group_fe == 'ret_fe' else 0.0  # Mod impuesto

                tax_percentage_iva_01 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if item_tax.tax_id.tax_group_fe  == 'iva_fe' else tax_percentage_iva_01
                tax_percentage_ica_03 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if item_tax.tax_id.tax_group_fe  == 'ica_fe' else tax_percentage_ica_03
                tax_percentage_inc_04 = self.env['account.tax'].search([('id', '=', item_tax.tax_id.id)]).amount if item_tax.tax_id.tax_group_fe  == 'ico_fe' else tax_percentage_inc_04 # Mod impuesto
                tax_percentage_ret_06 = self.env['account.tax'].search([('id', '=',item_tax.tax_id.id)]).amount if item_tax.tax_id.tax_group_fe == 'ret_fe' else tax_percentage_ret_06

                invoice_lines = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id), ('invoice_line_tax_ids', 'in', item_tax.tax_id.id)])
                for invoice_line in invoice_lines:
                    total_base_iva_01 += invoice_line.price_subtotal if item_tax.tax_id.tax_group_fe  == 'iva_fe' else 0
                    total_base_ica_03 += invoice_line.price_subtotal if item_tax.tax_id.tax_group_fe  == 'ica_fe' else 0
                    total_base_inc_04 += invoice_line.price_subtotal if item_tax.tax_id.tax_group_fe  == 'ico_fe' else 0 # Mod impuesto
                    total_base_ret_06 += invoice_line.price_subtotal if item_tax.tax_id.tax_group_fe == 'ret_fe' else 0

                if iva_01 != 0.00 and total_base_iva_01 == 0.00 and item_tax.tax_id.tax_group_fe == 'iva_fe':
                    total_base_iva_01 = item_tax.invoice_id.amount_untaxed
                if ica_03 != 0.00 and total_base_ica_03 == 0.00 and item_tax.tax_id.tax_group_fe == 'ica_fe':
                    total_base_ica_03 = item_tax.invoice_id.amount_untaxed
                if inc_04 != 0.00 and total_base_inc_04 == 0.00 and item_tax.tax_id.tax_group_fe == 'ico_fe':
                    total_base_inc_04 = item_tax.invoice_id.amount_untaxed

                if ret_06 != 0.00 and total_base_ret_06 == 0.00 and item_tax.tax_id.tax_group_fe == 'ret_fe':
                    total_base_ret_06 = item_tax.invoice_id.amount_untaxed

                if iva_01 and item_tax.tax_id.tributes == '01':
                    dic_taxs_data['iva_' + str(iva_lines)] = self._complements_second_decimal_total(item_tax.amount_total)
                    dic_taxs_data['tax_percentage_iva_' + str(iva_lines)] = self._complements_second_decimal_total(item_tax.tax_id.amount)
                    dic_taxs_data['total_base_iva_' + str(iva_lines)] = self._complements_second_decimal_total(item_tax.base)
                    iva_lines += 1

                if ret_06:
                    dic_taxs_data['ret_' + str(ret_lines)] = self._complements_second_decimal_total(ret_06 * -1)
                    dic_taxs_data['tax_percentage_ret_' + str(ret_lines)] = str(tax_percentage_ret_06 * -1)
                    dic_taxs_data['total_base_ret_' + str(ret_lines)] = self._complements_second_decimal_total(total_base_ret_06)
                    ret_lines += 1

        dic_taxs_data['iva_lines'] = iva_lines - 1
        dic_taxs_data['ret_lines'] = ret_lines - 1

        dic_taxs_data['ica_03'] = self._complements_second_decimal_total(ica_03 if ica_03 >= 0.00 else ica_03 * -1.00)
        dic_taxs_data['tax_percentage_ica_03'] = self._complements_second_decimal_total(tax_percentage_ica_03 if tax_percentage_ica_03 >= 0.00 else tax_percentage_ica_03 * -1.00)
        dic_taxs_data['total_base_ica_03'] = self._complements_second_decimal_total(total_base_ica_03 if total_base_ica_03 >= 0.00 else total_base_ica_03 * -1.00)
        
        dic_taxs_data['inc_04'] = self._complements_second_decimal_total(inc_04) # Mod impuesto
        dic_taxs_data['tax_percentage_inc_04'] = self._complements_second_decimal_total(tax_percentage_inc_04) # Mod impuesto
        dic_taxs_data['total_base_inc_04'] = self._complements_second_decimal_total(total_base_inc_04) # Mod impuesto

        return dic_taxs_data


    @api.model
    def _generate_taxs_data_xml(self, template_tax_data_xml, data_taxs, CurrencyID, document_type):
        data_tax_xml = ''
        # iva_01
        SumTaxTotalTaxAmount = 0
        TaxRoundingAmount = 0
        for iva_line in range(data_taxs.get('iva_lines', 1)):
            iva_line_str = str(iva_line + 1)
            if data_taxs['iva_' + iva_line_str] != '0.00':
                SumTaxTotalTaxAmount += float(
                    data_taxs['iva_' + iva_line_str])  # Importe Impuesto (detalle): Importe del impuesto retenido
                TaxTotalTaxAmount = str(data_taxs['iva_' + iva_line_str])
                TaxTotalTaxEvidenceIndicator = 'false' if data_taxs[
                                                              'iva_' + iva_line_str] == 0.00 else 'true'  # Indica que el elemento es un Impuesto retenido (7.1.1) y no un impuesto (8.1.1) True
                TaxTotalTaxableAmount = str(data_taxs[
                                                'total_base_iva_' + iva_line_str])  # 7.1.1.1 / 8.1.1.1 - Base Imponible: Base Imponible sobre la que se calcula la retención de impuesto
                TaxTotalPercent = str(data_taxs[
                                          'tax_percentage_iva_' + iva_line_str])  # 7.1.1.3 / 8.1.1.3 - Porcentaje: Porcentaje a aplicar
                TaxTotalTaxSchemeID = '01'  # 7.1.1.2 - Tipo: Tipo o clase impuesto. Concepto fiscal por el que se tributa. Debería si un campo que referencia a una lista de códigos. En la lista deberían aparecer los impuestos estatales o nacionales. Código de impuesto
                TaxTotalName = 'IVA'

                imp_2 = float(data_taxs['total_base_iva_' + iva_line_str])
                imp_6 = float(data_taxs['tax_percentage_iva_' + iva_line_str])
                imp_4 = imp_2 * imp_6 / 100
                imp_6_imp_2 = (imp_2 * imp_6) / 100
                TaxRoundingAmount += imp_6_imp_2 - imp_4

                data_tax_xml += template_tax_data_xml % {'TaxTotalTaxAmount': TaxTotalTaxAmount,
                                                         # 'TaxTotalTaxEvidenceIndicator' : TaxTotalTaxEvidenceIndicator,
                                                         'TaxTotalTaxableAmount': TaxTotalTaxableAmount,
                                                         'TaxTotalPercent': TaxTotalPercent,
                                                         'TaxTotalName': TaxTotalName,
                                                         'TaxTotalTaxSchemeID': TaxTotalTaxSchemeID,
                                                         'CurrencyID': CurrencyID
                                                         }

        if SumTaxTotalTaxAmount:
            data_tax_xml = """
            <cac:TaxTotal>
                
                <cbc:TaxAmount currencyID="%(CurrencyID)s">%(TaxTotalTaxAmount)s</cbc:TaxAmount>
                <cbc:RoundingAmount currencyID="%(CurrencyID)s">%(TaxRoundingAmount)s</cbc:RoundingAmount>
                %(Taxes)s
            </cac:TaxTotal>
            """ % {
                'TaxRoundingAmount': self._complements_second_decimal_total(TaxRoundingAmount),
                'TaxTotalTaxAmount': str(SumTaxTotalTaxAmount),
                'CurrencyID': CurrencyID,
                'Taxes': data_tax_xml
            }

        # Solo si es factura normal se coloca en la estructura WithholdingTaxTotal
        if document_type != 'f':
            return data_tax_xml

        # ica_03
        if data_taxs['ica_03'] != '0.00':
            TaxTotalTaxAmount = str(data_taxs['ica_03'])  # Importe Impuesto (detalle): Importe del impuesto retenido
            TaxTotalTaxEvidenceIndicator = 'false' if data_taxs[
                                                          'ica_03'] == 0.00 else 'true'  # Indica que el elemento es un Impuesto retenido (7.1.1) y no un impuesto (8.1.1) True
            TaxTotalTaxableAmount = str(data_taxs[
                                            'total_base_ica_03'])  # 7.1.1.1 / 8.1.1.1 - Base Imponible: Base Imponible sobre la que se calcula la retención de impuesto
            TaxTotalPercent = str(
                data_taxs['tax_percentage_ica_03'])  # 7.1.1.3 / 8.1.1.3 - Porcentaje: Porcentaje a aplicar
            TaxTotalTaxSchemeID = '03'
            TaxTotalName = 'ICA'  # 7.1.1.2 - Tipo: Tipo o clase impuesto. Concepto fiscal por el que se tributa. Debería si un campo que referencia a una lista de códigos. En la lista deberían aparecer los impuestos estatales o nacionales. Código de impuesto
            data_tax_xml_ica = template_tax_data_xml.replace('<cbc:Percent>%(TaxTotalPercent)s</cbc:Percent>', '') % {'TaxTotalTaxAmount': TaxTotalTaxAmount,
                                                        # 'TaxTotalTaxEvidenceIndicator' : TaxTotalTaxEvidenceIndicator,
                                                        'TaxTotalTaxableAmount': TaxTotalTaxableAmount,
                                                        'TaxTotalPercent': TaxTotalPercent,
                                                        'TaxTotalName': TaxTotalName,
                                                        'TaxTotalTaxSchemeID': TaxTotalTaxSchemeID,
                                                        'CurrencyID': CurrencyID
                                                        }
            data_tax_xml += """
                        <cac:WithholdingTaxTotal>
                            <cbc:TaxAmount currencyID="%(CurrencyID)s">%(TaxTotalTaxAmount)s</cbc:TaxAmount>
                            %(Taxes)s
                        </cac:WithholdingTaxTotal>
                        """ % {
                'TaxTotalTaxAmount': str(TaxTotalTaxAmount),
                'CurrencyID': CurrencyID,
                'Taxes': data_tax_xml_ica
            }

        # inc_04
        if data_taxs['inc_04'] != '0.00':
            TaxTotalTaxAmount = str(data_taxs['inc_04'])  # Importe Impuesto (detalle): Importe del impuesto retenido
            TaxTotalTaxEvidenceIndicator = 'false' if data_taxs[
                                                          'inc_04'] == 0.00 else 'true'  # Indica que el elemento es un Impuesto retenido (7.1.1) y no un impuesto (8.1.1) True
            TaxTotalTaxableAmount = str(data_taxs[
                                            'total_base_inc_04'])  # 7.1.1.1 / 8.1.1.1 - Base Imponible: Base Imponible sobre la que se calcula la retención de impuesto
            TaxTotalPercent = str(
                data_taxs['tax_percentage_inc_04'])  # 7.1.1.3 / 8.1.1.3 - Porcentaje: Porcentaje a aplicar
            TaxTotalTaxSchemeID = '04'
            TaxTotalName = 'INC'  # 7.1.1.2 - Tipo: Tipo o clase impuesto. Concepto fiscal por el que se tributa. Debería si un campo que referencia a una lista de códigos. En la lista deberían aparecer los impuestos estatales o nacionales. Código de impuesto
            data_tax_xml_inc = template_tax_data_xml % {'TaxTotalTaxAmount': TaxTotalTaxAmount,
                                                        # 'TaxTotalTaxEvidenceIndicator' : TaxTotalTaxEvidenceIndicator,
                                                        'TaxTotalTaxableAmount': TaxTotalTaxableAmount,
                                                        'TaxTotalPercent': TaxTotalPercent,
                                                        'TaxTotalName': TaxTotalName,
                                                        'TaxTotalTaxSchemeID': TaxTotalTaxSchemeID,
                                                        'CurrencyID': CurrencyID
                                                        }

            data_tax_xml += """
                    <cac:WithholdingTaxTotal>
                        <cbc:TaxAmount currencyID="%(CurrencyID)s">%(TaxTotalTaxAmount)s</cbc:TaxAmount>
                        %(Taxes)s
                    </cac:WithholdingTaxTotal>
                                    """ % {
                'TaxTotalTaxAmount': str(TaxTotalTaxAmount),
                'CurrencyID': CurrencyID,
                'Taxes': data_tax_xml_inc
            }

        # ret_06
        data_tax_xml_ret = ''
        SumTaxTotalTaxAmount = 0
        for ret_line in range(data_taxs.get('ret_lines', 1)):
            ret_line_str = str(ret_line + 1)
            if data_taxs['ret_' + ret_line_str] != '0.00':
                SumTaxTotalTaxAmount += float(
                    data_taxs['ret_' + ret_line_str])  # Importe Impuesto (detalle): Importe del impuesto retenido
                TaxTotalTaxAmount = str(data_taxs['ret_' + ret_line_str])
                TaxTotalTaxEvidenceIndicator = 'false' if data_taxs[
                                                              'ret_' + ret_line_str] == 0.00 else 'true'  # Indica que el elemento es un Impuesto retenido (7.1.1) y no un impuesto (8.1.1) True
                TaxTotalTaxableAmount = str(data_taxs[
                                                'total_base_ret_' + ret_line_str])  # 7.1.1.1 / 8.1.1.1 - Base Imponible: Base Imponible sobre la que se calcula la retención de impuesto
                TaxTotalPercent = str(data_taxs[
                                          'tax_percentage_ret_' + ret_line_str])  # 7.1.1.3 / 8.1.1.3 - Porcentaje: Porcentaje a aplicar
                TaxTotalTaxSchemeID = '06'  # 7.1.1.2 - Tipo: Tipo o clase impuesto. Concepto fiscal por el que se tributa. Debería si un campo que referencia a una lista de códigos. En la lista deberían aparecer los impuestos estatales o nacionales. Código de impuesto
                TaxTotalName = 'ReteRenta'
                data_tax_xml_ret += template_tax_data_xml % {'TaxTotalTaxAmount': TaxTotalTaxAmount,
                                                             # 'TaxTotalTaxEvidenceIndicator' : TaxTotalTaxEvidenceIndicator,
                                                             'TaxTotalTaxableAmount': TaxTotalTaxableAmount,
                                                             'TaxTotalPercent': TaxTotalPercent,
                                                             'TaxTotalName': TaxTotalName,
                                                             'TaxTotalTaxSchemeID': TaxTotalTaxSchemeID,
                                                             'CurrencyID': CurrencyID
                                                             }

        if SumTaxTotalTaxAmount:
            data_tax_xml += """
            <cac:WithholdingTaxTotal>
                <cbc:TaxAmount currencyID="%(CurrencyID)s">%(TaxTotalTaxAmount)s</cbc:TaxAmount>
                %(Taxes)s
            </cac:WithholdingTaxTotal>
            """ % {
                'TaxTotalTaxAmount': self._complements_second_decimal_total(SumTaxTotalTaxAmount),
                'CurrencyID': CurrencyID,
                'Taxes': data_tax_xml_ret
            }

        return data_tax_xml


    def _generate_lines_data_xml(self, template_line_data_xml, invoice_id, CurrencyID):
        ILLinea = 0
        data_line_xml = ''
        InvoiceLineTaxSubtotal_xml = ''
        template_InvoiceLineTaxSubtotal_xml = self._template_InvoiceLineTaxSubtotal_xml()
        data_lines_doc = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)])
        for data_line in data_lines_doc:
            ID_UNSPSC = data_line.product_id.product_UNSPSC_id.product
            if data_line.price_subtotal:
                ILLinea += 1
                ILInvoicedQuantity = self._complements_second_decimal_total(data_line.quantity)           # 13.1.1.9 - Cantidad: Cantidad del artículo solicitado. Número de unidades servidas/prestadas.
                ILLineExtensionAmount = self._complements_second_decimal_total(data_line.price_subtotal)  # 13.1.1.12 - Costo Total: Coste Total. Resultado: Unidad de Medida x Precio Unidad.
                ILChargeIndicator = 'true'                                                          # Indica que el elemento es un Cargo (5.1.1) y no un descuento (4.1.1)
                ILAmount =  self._complements_second_decimal_total(data_line.discount)                    # Valor Descuento: Importe total a descontar.
                ILDescription = self._replace_character_especial(data_line.name)
                ILPriceAmount = self._complements_second_decimal_total(data_line.price_unit)              # Precio Unitario
                BrandName = self._replace_character_especial(data_line.product_id.brand_id.name if data_line.product_id.brand_id else '')
                ModelName = self._replace_character_especial(data_line.product_id.model_id.name if data_line.product_id.model_id else '')
               
                # Valor del tributo
                ILTaxAmount = 0.00
                InvoiceLineTaxSubtotal_xml = ''
                TaxRoundingAmount = 0
                for line_tax in data_line.invoice_line_tax_ids:
                    tax = self.env['account.tax'].search([('id', '=', line_tax.id)])
                    #ILTaxAmount += data_line.price_subtotal * (tax.amount / 100.00)
                    ILTaxAmount += data_line.price_total - data_line.price_subtotal
                    ILTaxAmount  = float(self._complements_second_decimal_total(ILTaxAmount))
                    #ILTaxAmountSubtotal = self._complements_second_decimal_total(data_line.price_subtotal * (tax.amount / 100.00))
                    #ILTaxAmountSubtotal = data_line.price_total - data_line.price_subtotal
                    ILTaxAmountSubtotal = self._complements_second_decimal_total(data_line.price_total - data_line.price_subtotal)
                    ILTaxableAmount = self._complements_second_decimal_total(data_line.price_subtotal)
                    ILPercent  = self._complements_second_decimal_total(tax.amount)
                    ILID = tax.tributes              
                    ILName = tributes[tax.tributes]  
                    # Nuevo ini

                    imp_2 = data_line.price_subtotal
                    imp_6 = tax.amount
                    imp_4 = imp_2 * imp_6 / 100
                    imp_6_imp_2 = (imp_2 * imp_6) / 100
                    TaxRoundingAmount += imp_6_imp_2 - imp_4

                    InvoiceLineTaxSubtotal_xml += template_InvoiceLineTaxSubtotal_xml % {
                                                            'ILTaxAmountSubtotal' : ILTaxAmountSubtotal,
                                                            'ILTaxableAmount' : ILTaxableAmount,
                                                            'ILPercent' : ILPercent,
                                                            'ILID' : ILID,
                                                            'ILName' : ILName,
                                                            'CurrencyID' : CurrencyID,

                                                            } 
                    # Nuevo fin 
                ILTaxAmount = self._complements_second_decimal_total(ILTaxAmount)
                InformationContentProviderParty = ''
                if data_line.product_id.product_tmpl_id.operation_type == '11':
                    InformationContentProviderParty = self._template_line_data_information_content_provider_party_xml()

                    if not data_line.invoice_id.mandante_id:
                        raise ValidationError(_(u'El Propietario o Mandante no se encuentra seleccionado, en la pestaña otra información puede seleccionarlo'))

                    InformationContentProviderParty = InformationContentProviderParty % {
                        'MandanteNumberIdentification' : data_line.invoice_id.mandante_id.xidentification,
                    }


                data_line_xml += template_line_data_xml % {'ILLinea' : ILLinea,
                                                        'ILInvoicedQuantity' : ILInvoicedQuantity,
                                                        'ILLineExtensionAmount' : ILLineExtensionAmount, # Ojo descuentos mas recargos de la linea
                                                        'ILAmount' : ILAmount,
                                                        'ILDescription' : ILDescription,
                                                        'BrandName' : BrandName,
                                                        'ModelName' : ModelName,
                                                        'ILPriceAmount' : ILPriceAmount,
                                                        'ILChargeIndicator' : ILChargeIndicator,
                                                        'ILTaxAmount' : ILTaxAmount,
                                                        'InvoiceLineTaxSubtotal' : InvoiceLineTaxSubtotal_xml,
                                                        'InformationContentProviderParty' : InformationContentProviderParty,
                                                        'CurrencyID' : CurrencyID,
                                                        'ID_UNSPSC' : ID_UNSPSC,
                                                        'TaxRoundingAmount':  self._complements_second_decimal_total(TaxRoundingAmount)
                                                        }
        return data_line_xml


    def _generate_credit_lines_data_xml(self , template_credit_line_data_xml, invoice_id, CurrencyID):
        ILLinea = 0
        data_credit_note_line_xml = ''
        data_lines_doc = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)])
        ILTaxAmount = 0.00
        InvoiceLineTaxSubtotal_xml = ''
        for data_line in data_lines_doc:
            ID_UNSPSC = data_line.product_id.product_UNSPSC_id.product
            ILLinea += 1
            ILInvoicedQuantity = self._complements_second_decimal_total(data_line.quantity)           # 13.1.1.9 - Cantidad: Cantidad del artículo solicitado. Número de unidades servidas/prestadas.
            ILLineExtensionAmount = self._complements_second_decimal_total(data_line.price_subtotal)  # 13.1.1.12 - Costo Total: Coste Total. Resultado: Unidad de Medida x Precio Unidad.
            ILChargeIndicator = 'true'                                                          # Indica que el elemento es un Cargo (5.1.1) y no un descuento (4.1.1)
            ILAmount =  self._complements_second_decimal_total(data_line.discount)                    # Valor Descuento: Importe total a descontar.
            ILDescription = self._replace_character_especial(data_line.name)
            ILPriceAmount = self._complements_second_decimal_total(data_line.price_unit)              # Precio Unitario
            BrandName = self._replace_character_especial(
                data_line.product_id.brand_id.name if data_line.product_id.brand_id else '')
            ModelName = self._replace_character_especial(
                data_line.product_id.model_id.name if data_line.product_id.model_id else '')
           
            # Valor del tributo
            ILTaxAmount = 0.00
            ILTaxableAmount =  0.00
            ILPercent  =  0.00
            ILID = ''           
            ILName = ''
            InvoiceLineTaxSubtotal_xml = ''
            TaxRoundingAmount = 0
            for line_tax in data_line.invoice_line_tax_ids:
                tax = self.env['account.tax'].search([('id', '=', line_tax.id)])
                #ILTaxAmount = self._complements_second_decimal_total(data_line.price_subtotal * (tax.amount / 100.00))
                #ILTaxAmount = self._complements_second_decimal_total(data_line.price_total - data_line.price_subtotal)
                ILTaxAmount = self._complements_second_decimal_total(data_line.price_total - data_line.price_subtotal)
                ILTaxableAmount = self._complements_second_decimal_total(data_line.price_subtotal)
                ILPercent  = self._complements_second_decimal_total(tax.amount)
                ILID = tax.tributes              
                ILName = tributes[tax.tributes]

                imp_2 = data_line.price_subtotal
                imp_6 = tax.amount
                imp_4 = imp_2 * imp_6 / 100
                imp_6_imp_2 = (imp_2 * imp_6) / 100
                TaxRoundingAmount += imp_6_imp_2 - imp_4

            InformationContentProviderParty = ''
            if data_line.product_id.product_tmpl_id.operation_type == '11':
                InformationContentProviderParty = self._template_line_data_information_content_provider_party_xml()

                if not data_line.invoice_id.mandante_id:
                    raise ValidationError(_(u'El Propietario o Mandante no se encuentra seleccionado, en la pestaña otra información puede seleccionarlo'))

                InformationContentProviderParty = InformationContentProviderParty % {
                    'MandanteNumberIdentification' : data_line.invoice_id.mandante_id.xidentification,
                }

            data_credit_note_line_xml += template_credit_line_data_xml % {'ILLinea' : ILLinea,
                                                    'ILInvoicedQuantity' : ILInvoicedQuantity,
                                                    'ILLineExtensionAmount' : ILLineExtensionAmount, # Ojo descuentos mas recargos de la linea
                                                    'ILAmount' : ILAmount,
                                                    'ILDescription' : ILDescription,
                                                    'BrandName' : BrandName,
                                                    'ModelName' : ModelName,
                                                    'ILPriceAmount' : ILPriceAmount,
                                                    'ILChargeIndicator' : ILChargeIndicator,
                                                    'ILTaxAmount' : ILTaxAmount,
                                                    'ILTaxableAmount' : ILTaxableAmount,
                                                    'ILPercent' : ILPercent,
                                                    'ILID' : ILID,
                                                    'ILName' : ILName,
                                                    'InformationContentProviderParty' : InformationContentProviderParty,
                                                    'CurrencyID' : CurrencyID,
                                                    'ID_UNSPSC' : ID_UNSPSC,
                                                    'TaxRoundingAmount': self._complements_second_decimal_total(TaxRoundingAmount)
                                                    }
        return data_credit_note_line_xml


    def _generate_debit_lines_data_xml(self , template_debit_line_data_xml, invoice_id,  CurrencyID):
        ILLinea = 0
        data_debit_note_line_xml = ''
        data_lines_doc = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)])
        for data_line in data_lines_doc:
            ID_UNSPSC = data_line.product_id.product_UNSPSC_id.product
            ILLinea += 1
            ILInvoicedQuantity = self._complements_second_decimal_total(data_line.quantity)           # 13.1.1.9 - Cantidad: Cantidad del artículo solicitado. Número de unidades servidas/prestadas.
            ILLineExtensionAmount = self._complements_second_decimal_total(data_line.price_subtotal)  # 13.1.1.12 - Costo Total: Coste Total. Resultado: Unidad de Medida x Precio Unidad.
            ILChargeIndicator = 'true'                                                          # Indica que el elemento es un Cargo (5.1.1) y no un descuento (4.1.1)
            ILAmount =  self._complements_second_decimal_total(data_line.discount)                    # Valor Descuento: Importe total a descontar.
            ILDescription = self._replace_character_especial(data_line.name)
            ILPriceAmount = self._complements_second_decimal_total(data_line.price_unit)              # Precio Unitario
            BrandName = self._replace_character_especial(
                data_line.product_id.brand_id.name if data_line.product_id.brand_id else '')
            ModelName = self._replace_character_especial(
                data_line.product_id.model_id.name if data_line.product_id.model_id else '')
           
            # Valor del tributo
            ILTaxAmount = 0.00
            ILTaxAmount = 0.00
            ILTaxableAmount =  0.00
            ILPercent  =  0.00
            ILID = ''           
            ILName = ''
            TaxRoundingAmount = 0
            InvoiceLineTaxSubtotal_xml = ''
            for line_tax in data_line.invoice_line_tax_ids:
                tax = self.env['account.tax'].search([('id', '=', line_tax.id)])
                #ILTaxAmount = self._complements_second_decimal_total(data_line.price_subtotal * (tax.amount / 100.00))
                #ILTaxAmount = self._complements_second_decimal_total(data_line.price_total - data_line.price_subtotal)
                ILTaxAmount  = self._complements_second_decimal_total(data_line.price_total - data_line.price_subtotal)
                ILTaxableAmount = self._complements_second_decimal_total(data_line.price_subtotal)
                ILPercent  = self._complements_second_decimal_total(tax.amount)
                ILID = tax.tributes              
                ILName = tributes[tax.tributes]

                imp_2 = data_line.price_subtotal
                imp_6 = tax.amount
                imp_4 = imp_2 * imp_6 / 100
                imp_6_imp_2 = (imp_2 * imp_6) / 100
                TaxRoundingAmount += imp_6_imp_2 - imp_4

            InformationContentProviderParty = ''
            if data_line.product_id.product_tmpl_id.operation_type == '11':
                InformationContentProviderParty = self._template_line_data_information_content_provider_party_xml()

                if not data_line.invoice_id.mandante_id:
                    raise ValidationError(_(u'El Propietario o Mandante no se encuentra seleccionado, en la pestaña otra información puede seleccionarlo'))

                InformationContentProviderParty = InformationContentProviderParty % {
                    'MandanteNumberIdentification' : data_line.invoice_id.mandante_id.xidentification,
                }

            data_debit_note_line_xml += template_debit_line_data_xml % {'ILLinea' : ILLinea,
                                                    'ILInvoicedQuantity' : ILInvoicedQuantity,
                                                    'ILLineExtensionAmount' : ILLineExtensionAmount, # Ojo descuentos mas recargos de la linea
                                                    'ILAmount' : ILAmount,
                                                    'ILDescription' : ILDescription,
                                                    'BrandName' : BrandName,
                                                    'ModelName' : ModelName,
                                                    'ILPriceAmount' : ILPriceAmount,
                                                    'ILChargeIndicator' : ILChargeIndicator,
                                                    'ILTaxAmount' : ILTaxAmount,
                                                    'ILTaxableAmount' : ILTaxableAmount,
                                                    'ILPercent' : ILPercent,
                                                    'ILID' : ILID,
                                                    'ILName' : ILName,
                                                    'InformationContentProviderParty' : InformationContentProviderParty,
                                                    'CurrencyID' : CurrencyID,
                                                    'ID_UNSPSC' : ID_UNSPSC,
                                                                        'TaxRoundingAmount': self._complements_second_decimal_total(
                                                                            TaxRoundingAmount)
                                                    }


        return data_debit_note_line_xml

    @api.model
    def _generate_cufe(self, invoice_id, NumFac, FecFac, HoraFac, ValFac, NitOFE, TipAdq, NumAdq, ClTec, ValPag, 
        data_taxs, TipoAmbiente):
        ValFac = str(ValFac)
        CodImp1 = '01'
        ValImp1 = 0

        for iva_line in range( data_taxs.get('iva_lines') ):
            iva_line_str = str(iva_line + 1)
            ValImp1 += float(data_taxs['iva_' + iva_line_str])

        ValImp1 = str('{0:.2f}'.format(ValImp1))
        CodImp2 = '04'
        ValImp2 = '0.00'
        CodImp3 = '03'
        ValImp3 = '0.00'
        ValPag  = str(ValPag)
        TipAdq  = str(TipAdq)
        CUFE = NumFac+FecFac+HoraFac+ValFac+CodImp1+ValImp1+CodImp2+ValImp2+CodImp3+ValImp3+ValPag+NitOFE+NumAdq+ClTec+TipoAmbiente
        CUFE = hashlib.sha384(CUFE.encode())
        CUFE = CUFE.hexdigest()
        return CUFE


    @api.model
    def _generate_cude(self, invoice_id, NumFac, FecFac, HoraFac, ValFac, NitOFE, TipAdq, NumAdq, PINSoftware, ValPag, 
        data_taxs, TipoAmbiente):
        CodImp1 = '01'
        ValImp1 = 0

        for iva_line in range(data_taxs.get('iva_lines')):
            iva_line_str = str(iva_line + 1)
            ValImp1 += float(data_taxs['iva_' + iva_line_str])

        ValImp1 = str('{0:.2f}'.format(ValImp1))
        CodImp2 = '04'
        ValImp2 = '0.00'
        CodImp3 = '03'
        ValImp3 = '0.00'
        ValPag  = str(ValPag)
        TipAdq  = str(TipAdq)
        CUDE = NumFac+FecFac+HoraFac+ValFac+CodImp1+ValImp1+CodImp2+ValImp2+CodImp3+ValImp3+ValPag+NitOFE+NumAdq+PINSoftware+TipoAmbiente
        CUDE = hashlib.sha384(CUDE.encode())
        CUDE = CUDE.hexdigest()
        return CUDE


    @api.model
    def _generate_signature_ref0(self, data_xml_document, document_repository, password):
        # 1er paso. Generar la referencia 0 que consiste en obtener keyvalue desde todo el xml del 
        #           documento electronico aplicando el algoritmo SHA256 y convirtiendolo a base64
        template_basic_data_fe_xml = data_xml_document
        template_basic_data_fe_xml = etree.tostring(etree.fromstring(template_basic_data_fe_xml), method="c14n", exclusive=False,with_comments=False,inclusive_ns_prefixes=None)
        data_xml_sha256 = hashlib.new('sha256', template_basic_data_fe_xml)
        data_xml_digest = data_xml_sha256.digest()
        data_xml_signature_ref_zero = base64.b64encode(data_xml_digest)
        data_xml_signature_ref_zero = data_xml_signature_ref_zero.decode()
        return data_xml_signature_ref_zero


    @api.model
    def _update_signature(self, template_signature_data_xml, data_xml_signature_ref_zero, data_public_certificate_base, 
                                data_xml_keyinfo_base, data_xml_politics, 
                                data_xml_SignedProperties_base, data_xml_SigningTime, dian_constants,
                                data_xml_SignatureValue, data_constants_document):
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
                                        'identifier' : data_constants_document['identifier'],
                                        'identifierkeyinfo' : data_constants_document['identifierkeyinfo'],                                        
                                        }
        return data_xml_signature


    @api.multi
    def _generate_signature_ref1(self, data_xml_keyinfo_generate, document_repository, password):
        # Generar la referencia 1 que consiste en obtener keyvalue desde el keyinfo contenido 
        # en el documento electrónico aplicando el algoritmo SHA256 y convirtiendolo a base64
        data_xml_keyinfo_generate = etree.tostring(etree.fromstring(data_xml_keyinfo_generate), method="c14n")
        data_xml_keyinfo_sha256 = hashlib.new('sha256', data_xml_keyinfo_generate)
        data_xml_keyinfo_digest = data_xml_keyinfo_sha256.digest()
        data_xml_keyinfo_base = base64.b64encode(data_xml_keyinfo_digest)
        data_xml_keyinfo_base = data_xml_keyinfo_base.decode()
        return data_xml_keyinfo_base


    def _generate_digestvalue_to(self, elementTo):
        # Generar el digestvalue de to
        elementTo = etree.tostring(etree.fromstring(elementTo), method="c14n")
        elementTo_sha256 = hashlib.new('sha256', elementTo)
        elementTo_digest = elementTo_sha256.digest()
        elementTo_base = base64.b64encode(elementTo_digest)
        elementTo_base = elementTo_base.decode()
        return elementTo_base


    @api.multi
    def _generate_signature_politics(self, document_repository):
        # Generar la referencia 2 que consiste en obtener keyvalue desde el documento de politica 
        # aplicando el algoritmo SHA1 antes del 20 de septimebre de 2016 y sha256 después  de esa 
        # fecha y convirtiendolo a base64. Se  puede utilizar como una constante ya que no variará 
        # en años segun lo indica la DIAN.
        #  
        # politicav2 = document_repository+'/politicadefirmav2.pdf'
        # politicav2 = open(politicav2,'r')
        # contenido_politicav2 = politicav2.read()
        # politicav2_sha256 = hashlib.new('sha256', contenido_politicav2)
        # politicav2_digest = politicav2_sha256.digest()
        # politicav2_base = base64.b64encode(politicav2_digest)
        # data_xml_politics = politicav2_base
        data_xml_politics = 'dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y='
        return data_xml_politics


    @api.multi
    def _generate_signature_ref2(self, data_xml_SignedProperties_generate):
        # Generar la referencia 2, se obtine desde el elemento SignedProperties que se 
        # encuentra en la firma aplicando el algoritmo SHA256 y convirtiendolo a base64.
        data_xml_SignedProperties_c14n = etree.tostring(etree.fromstring(data_xml_SignedProperties_generate), method="c14n")
        data_xml_SignedProperties_sha256 = hashlib.new('sha256', data_xml_SignedProperties_c14n)
        data_xml_SignedProperties_digest = data_xml_SignedProperties_sha256.digest()
        data_xml_SignedProperties_base = base64.b64encode(data_xml_SignedProperties_digest)
        data_xml_SignedProperties_base = data_xml_SignedProperties_base.decode()
        return data_xml_SignedProperties_base


    @api.multi
    def _generate_CertDigestDigestValue(self, digital_certificate, password, document_repository, archivo_certificado):
        archivo_key = document_repository +'/'+archivo_certificado
        key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password) 
        certificate = hashlib.sha256(crypto.dump_certificate(crypto.FILETYPE_ASN1, key.get_certificate()))
        CertDigestDigestValue = base64.b64encode(certificate.digest())
        CertDigestDigestValue = CertDigestDigestValue.decode()
        return CertDigestDigestValue


    @api.multi
    def _generate_SignatureValue(self, document_repository, password, data_xml_SignedInfo_generate, 
            archivo_pem, archivo_certificado):
        data_xml_SignatureValue_c14n = etree.tostring(etree.fromstring(data_xml_SignedInfo_generate), method="c14n", exclusive=False, with_comments=False)
        archivo_key = document_repository+'/'+archivo_certificado
        try:
            key = crypto.load_pkcs12(open(archivo_key, 'rb').read(), password)  
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        try:
            signature = crypto.sign(key.get_privatekey(), data_xml_SignatureValue_c14n, 'sha256')               
        except Exception as ex:
            raise UserError(tools.ustr(ex))
        SignatureValue = base64.b64encode(signature)
        SignatureValue = SignatureValue.decode()
        archivo_pem = document_repository+'/'+archivo_pem
        pem = crypto.load_certificate(crypto.FILETYPE_PEM, open(archivo_pem, 'rb').read())
        try:
            validacion = crypto.verify(pem, signature, data_xml_SignatureValue_c14n, 'sha256')
        except:
            raise ValidationError("Firma no fué validada exitosamente")
        #serial = key.get_certificate().get_serial_number()
        return SignatureValue


    @api.model
    def _get_doctype(self, doctype, is_debit_note, in_contingency_4):  
        if doctype == 'out_invoice' and is_debit_note == False: # Es una factura
            if self.document_id.partner_id.country_id.code != 'CO':
                return '02'
            if self.contingency_3 == False and self.contingency_4 == False  and in_contingency_4 == False:
                docdian = '01'
            elif self.contingency_3 == True and in_contingency_4 == False:
                docdian = '03' 
            elif self.contingency_4 == True and in_contingency_4 == False:
                docdian = '04'
            elif in_contingency_4 == True:
                docdian = '04'
        if doctype == 'out_refund':
            docdian = '91'
        if doctype == 'out_invoice' and is_debit_note == True:
            docdian = '92'
        return docdian


    @api.model
    def _get_lines_invoice(self, invoice_id):
        lines = 0
        move_lines = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id)])
        for move_line in move_lines:
            if move_line.price_subtotal != 0.00:
                lines += 1
        return lines


    @api.model
    def _get_time(self):
        fmt = "%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_time = now_utc.strftime(fmt)
        return now_time


    @api.model
    def _get_time_colombia(self):
        fmt = "%H:%M:%S-05:00"
        now_utc = datetime.now(timezone('UTC'))
        now_time = now_utc.strftime(fmt)
        return now_time

    
    @api.multi
    def _generate_signature_signingtime(self):
        fmt = "%Y-%m-%dT%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc
        data_xml_SigningTime = now_bogota.strftime(fmt)+'-05:00'
        return data_xml_SigningTime


    @api.model
    def _generate_xml_filename(self, data_resolution, NitSinDV, doctype, is_debit_note):
        if doctype == 'out_invoice' and is_debit_note == False:
            docdian = 'face_f'
        elif doctype == 'out_refund':
            docdian = 'face_c'
        elif doctype == 'out_invoice' and is_debit_note:
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


    def _generate_zip_filename(self, data_resolution, NitSinDV, doctype, is_debit_note):
        if doctype == 'out_invoice' and is_debit_note == False:
            docdian = 'face_f'
        elif doctype == 'out_refund':
            docdian = 'face_c'
        elif doctype == 'out_invoice' and is_debit_note:
            docdian = 'face_d'
        nit = NitSinDV.zfill(10)
        # len_prefix = len(data_resolution['Prefix'])
        # len_invoice = len(data_resolution['InvoiceID'])        
        secuenciador = data_resolution['InvoiceID'] 
        dian_code_int = int(re.sub('\D', '', secuenciador)) 
        #dian_code_int = int(data_resolution['InvoiceID'][len_prefix:len_invoice])
        dian_code_hex = self.IntToHex(dian_code_int)
        dian_code_hex.zfill(10)
        file_name_zip = docdian + NitSinDV.zfill(10) + dian_code_hex.zfill(10) + '.zip'
        return file_name_zip


    def _generate_zip_content(self, FileNameXML, FileNameZIP, data_xml_document, document_repository):
        # Almacena archvio XML
        xml_file = document_repository +'/' + FileNameXML
        f = open (xml_file,'w')
        f.write(str(data_xml_document))
        f.close()
        # Comprime archvio XML
        zip_file = document_repository + '/' + FileNameZIP
        zf = zipfile.ZipFile(zip_file, mode="w")
        try:
            zf.write(xml_file, os.path.relpath(xml_file, document_repository), compress_type=compression)
        finally:
            zf.close()
        # Obtiene datos comprimidos
        data_xml = zip_file
        data_xml = open(data_xml,'rb')
        data_xml = data_xml.read()
        contenido_data_xml_b64 = base64.b64encode(data_xml)
        contenido_data_xml_b64 = contenido_data_xml_b64.decode()
        return contenido_data_xml_b64

    def _read_zip_content(self, FileNameXML, FileNameZIP, data_xml_document, document_repository):
        # Obtiene datos comprimidos
        zip_file = document_repository + '/' + FileNameZIP
        data_xml = zip_file
        data_xml = open(data_xml,'rb')
        data_xml = data_xml.read()
        contenido_data_xml_b64 = base64.b64encode(data_xml)
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
        ValIva = data_taxs['iva_1'] if 'iva_1' in data_taxs else '0'
        ValOtroIm = data_taxs['inc_04'] + data_taxs['ica_03'] 
        ValTotFac = data_constants_document['TotalTaxInclusiveAmount']  
        datos_qr = ' NumFac: '+NumFac+' FecFac: '+FecFac+' HorFac: '+Time+' NitFac: '+NitOFE+' DocAdq: '+DocAdq+' ValFac: '+str(ValFac)+' ValIva: '+str(ValIva)+' ValOtroIm: '+str(ValOtroIm)+' ValTotFac: '+str(ValTotFac)+' CUFE: '+CUFE
        # Genera código QR
        qr_code = pyqrcode.create(datos_qr)
        qr_code = qr_code.png_as_base64_str(scale=2)
        return qr_code


    @api.model
    def _generate_nonce(self, InvoiceID, seed_code):
        # NonceEncodingType. Se obtiene de:
        # 1. Calcular un valor aleatorio cuya semilla será definida y solamante conocida por el facturador 
        # electrónico 
        # 2. Convertir a Base 64 el valor aleatorio obtenido.
        nonce = randint(1,seed_code)
        nonce = base64.b64encode((InvoiceID+str(nonce)).encode())
        nonce = nonce.decode()
        return nonce


    def _generate_software_security_code(self, software_identification_code, software_pin, NroDocumento):
        software_security_code = hashlib.sha384((software_identification_code + software_pin + NroDocumento).encode())
        software_security_code = software_security_code.hexdigest()
        return  software_security_code 


    def _generate_datetime_timestamp(self):
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        #now_utc = datetime.now(timezone('UTC'))
        now_bogota = datetime.now(timezone('UTC'))
        #now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        Created = now_bogota.strftime(fmt)[:-3]+'Z'      
        now_bogota = now_bogota + timedelta(minutes=5) 
        Expires = now_bogota.strftime(fmt)[:-3]+'Z'
        timestamp = {'Created' : Created,
            'Expires' : Expires
        }   
        return timestamp


    def _generate_datetime_IssueDate(self):
        date_invoice_cufe = {}
        fmtSend = "%Y-%m-%dT%H:%M:%S"
        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc
        #now_bogota = now_utc.astimezone(timezone('America/Bogota'))
        date_invoice_cufe['IssueDateSend'] = now_bogota.strftime(fmtSend)
        fmtCUFE = "%Y-%m-%d"
        date_invoice_cufe['IssueDateCufe'] = now_bogota.strftime(fmtCUFE)
        fmtInvoice = "%Y-%m-%d"
        date_invoice_cufe['IssueDate'] = now_bogota.strftime(fmtInvoice)
        return date_invoice_cufe


    def _complements_second_decimal(self, amount):
        amount_dec = round(((amount - int(amount)) * 100.0),2)
        amount_int = int(amount_dec)
        if  amount_int % 10 == 0:
            amount = str(amount) + '0'
        else: 
            amount = str(amount)
        #amount = str(int(amount)) + (str((amount - int(amount)))[1:4])
        return amount


    def _complements_second_decimal_total(self, amount):
        """amount = str(int(amount)) + (str((amount - int(amount)))[1:4])
        amount = self._complements_second_decimal(float(amount))
        return amount"""
        if amount:
            return str('{0:.2f}'.format((amount)))
        else:
            return "0.00"


    def _template_SendTestSetAsyncsend_xml(self):
        template_SendTestSetAsyncsend_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:SendTestSetAsync>
            <wcf:fileName>%(fileName)s</wcf:fileName>
            <wcf:contentFile>%(contentFile)s</wcf:contentFile>
            <wcf:testSetId>%(testSetId)s</wcf:testSetId>
        </wcf:SendTestSetAsync>
    </soap:Body>
</soap:Envelope>
"""
        return template_SendTestSetAsyncsend_xml


    @api.model
    def _generate_SendTestSetAsync_send_xml(self, template_send_data_xml, fileName, contentFile, Created, 
        testSetId, identifier, Expires, Certificate, identifierSecurityToken, identifierTo):
        data_send_xml = template_send_data_xml % {
                        'fileName' : fileName,
                        'contentFile' : contentFile,
                        'testSetId' : testSetId,
                        'identifier' : identifier,
                        'Created' : Created,
                        'Expires' : Expires,
                        'Certificate' : Certificate,
                        'identifierSecurityToken' : identifierSecurityToken,
                        'identifierTo' : identifierTo,
                        }
        return data_send_xml


    def _template_SendBillAsyncsend_xml(self):
        template_SendBillAsyncsend_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendBillAsync</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:SendBillAsync>
            <wcf:fileName>%(fileName)s</wcf:fileName>
            <wcf:contentFile>%(contentFile)s</wcf:contentFile>
        </wcf:SendBillAsync>
    </soap:Body>
</soap:Envelope>
"""
        return template_SendBillAsyncsend_xml

            # <wcf:testSetId>%(testSetId)s</wcf:testSetId>


    @api.model
    def _generate_SendBillAsync_send_xml(self, template_send_data_xml, fileName, contentFile, Created, 
        testSetId, identifier, Expires, Certificate, identifierSecurityToken, identifierTo):
        data_send_xml = template_send_data_xml % {
                        'fileName' : fileName,
                        'contentFile' : contentFile,
                        'testSetId' : testSetId,
                        'identifier' : identifier,
                        'Created' : Created,
                        'Expires' : Expires,
                        'Certificate' : Certificate,
                        'identifierSecurityToken' : identifierSecurityToken,
                        'identifierTo' : identifierTo,
                        }
        return data_send_xml


#     def _template_GetNumberingRange_xml(self):
#         template_GetNumberingRange_xml = """
# <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
#     <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
#         <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
#             <wsu:Timestamp wsu:Id="TS-%(identifier)s">
#                 <wsu:Created>%(Created)s</wsu:Created>
#                 <wsu:Expires>%(Expires)s</wsu:Expires>
#             </wsu:Timestamp>
#             <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
#             <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
#                 <ds:SignedInfo>
#                     <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
#                         <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
#                     </ds:CanonicalizationMethod>
#                     <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
#                     <ds:Reference URI="#ID-%(identifierTo)s">
#                         <ds:Transforms>
#                             <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
#                                 <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
#                             </ds:Transform>
#                         </ds:Transforms>
#                         <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
#                         <ds:DigestValue></ds:DigestValue>
#                     </ds:Reference>
#                 </ds:SignedInfo>
#                 <ds:SignatureValue></ds:SignatureValue>
#                 <ds:KeyInfo Id="KI-%(identifier)s">
#                     <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
#                         <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
#                     </wsse:SecurityTokenReference>
#                 </ds:KeyInfo>
#             </ds:Signature>
#         </wsse:Security>
#         <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetNumberingRange</wsa:Action>
#         <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
#     </soap:Header>
#     <soap:Body>
#         <wcf:GetNumberingRange>
#             <wcf:accountCode>%(accountCode)s</wcf:accountCode>
#             <wcf:accountCodeT>%(accountCodeT)s</wcf:accountCodeT>
#             <wcf:softwareCode>%(softwareCode)s</wcf:softwareCode>
#         </wcf:GetNumberingRange>
#     </soap:Body>
# </soap:Envelope>
# """
#         return template_GetNumberingRange_xml


#     @api.model
#     def _generate_GetNumberingRange_send_xml(self, template_getstatus_send_data_xml, identifier, Created, 
#         Expires,  Certificate, accountCode, accountCodeT, softwareCode, 
#         identifierSecurityToken, identifierTo):
#         data_consult_numbering_range_send_xml = template_getstatus_send_data_xml % {
#                         'identifier' : identifier,
#                         'Created' : Created,
#                         'Expires' : Expires,
#                         'Certificate' : Certificate,
#                         'accountCode' : accountCode,
#                         'accountCodeT' : accountCodeT,
#                         'softwareCode' : softwareCode,
#                         'identifierSecurityToken' : identifierSecurityToken,
#                         'identifierTo' : identifierTo,
#                     }
#         return data_consult_numbering_range_send_xml


    def _template_GetStatus_xml(self):
        template_GetStatus_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatusZip</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:GetStatusZip>
            <wcf:trackId>%(trackId)s</wcf:trackId>
        </wcf:GetStatusZip>
    </soap:Body>
</soap:Envelope>
"""
        return template_GetStatus_xml


    @api.model
    def _generate_GetStatus_send_xml(self, template_getstatus_send_data_xml, identifier, Created, Expires,  Certificate, 
        identifierSecurityToken, identifierTo, trackId):
        data_getstatus_send_xml = template_getstatus_send_data_xml % {
                        'identifier' : identifier,
                        'Created' : Created,
                        'Expires' : Expires,
                        'Certificate' : Certificate,
                        'identifierSecurityToken' : identifierSecurityToken,
                        'identifierTo' : identifierTo,
                        'trackId' : trackId,
                    }
        return data_getstatus_send_xml   


    def _template_GetStatusExist_xml(self):
        template_GetStatus_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatus</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:GetStatus>
            <wcf:trackId>%(trackId)s</wcf:trackId>
        </wcf:GetStatus>
    </soap:Body>
</soap:Envelope>
"""
        return template_GetStatus_xml


    def _template_GetStatusExistTest_xml(self):
        template_GetStatus_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatus</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:GetStatus>
            <wcf:trackId>%(trackId)s</wcf:trackId>
        </wcf:GetStatus>
    </soap:Body>
</soap:Envelope>
"""
        return template_GetStatus_xml


    # @api.model
    # def _generate_GetTaxPayer_send_xml(self, template_getstatus_send_data_xml, identifier, Created, Expires,  Certificate, 
    #     identifierSecurityToken, identifierTo):
    #     data_getstatus_send_xml = template_getstatus_send_data_xml % {
    #                     'identifier' : identifier,
    #                     'Created' : Created,
    #                     'Expires' : Expires,
    #                     'Certificate' : Certificate,
    #                     'identifierSecurityToken' : identifierSecurityToken,
    #                     'identifierTo' : identifierTo,
    #                 }
    #     return data_getstatus_send_xml  


    def _template_SendBillSyncTestsend_xml(self):
        template_SendBillSyncTestsend_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:SendTestSetAsync>
            <wcf:fileName>%(fileName)s</wcf:fileName>
            <wcf:contentFile>%(contentFile)s</wcf:contentFile>
            <wcf:testSetId>%(testSetId)s</wcf:testSetId>
        </wcf:SendTestSetAsync>
    </soap:Body>
</soap:Envelope>
"""
        return template_SendBillSyncTestsend_xml


    @api.model
    def _generate_SendBillSyncTest_send_xml(self, template_send_data_xml, fileName, contentFile, Created, 
        testSetId, identifier, Expires, Certificate, identifierSecurityToken, identifierTo):
        data_send_xml = template_send_data_xml % {
                        'fileName' : fileName,
                        'contentFile' : contentFile,
                        'testSetId' : testSetId,
                        'identifier' : identifier,
                        'Created' : Created,
                        'Expires' : Expires,
                        'Certificate' : Certificate,
                        'identifierSecurityToken' : identifierSecurityToken,
                        'identifierTo' : identifierTo,
                        }
        return data_send_xml

# <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
#     <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
#         <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
#             <wsu:Timestamp wsu:Id="TS-%(identifier)s">
#                 <wsu:Created>%(Created)s</wsu:Created>
#                 <wsu:Expires>%(Expires)s</wsu:Expires>
#             </wsu:Timestamp>
#             <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
#             <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
#                 <ds:SignedInfo>
#                     <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
#                         <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
#                     </ds:CanonicalizationMethod>
#                     <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
#                     <ds:Reference URI="#ID-%(identifierTo)s">
#                         <ds:Transforms>
#                             <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
#                                 <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
#                             </ds:Transform>
#                         </ds:Transforms>
#                         <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
#                         <ds:DigestValue></ds:DigestValue>
#                     </ds:Reference>
#                 </ds:SignedInfo>
#                 <ds:SignatureValue></ds:SignatureValue>
#                 <ds:KeyInfo Id="KI-%(identifier)s">
#                     <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
#                         <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
#                     </wsse:SecurityTokenReference>
#                 </ds:KeyInfo>
#             </ds:Signature>
#         </wsse:Security>
#         <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendBillSync</wsa:Action>
#         <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
#     </soap:Header>
#     <soap:Body>
#         <wcf:SendBillSync>
#             <wcf:fileName>%(fileName)s</wcf:fileName>
#             <wcf:contentFile>%(contentFile)s</wcf:contentFile>
#         </wcf:SendBillSync>
#     </soap:Body>
# </soap:Envelope>
# """

    def _template_SendBillSyncsend_xml(self):
        template_SendBillSyncsend_xml = """
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia">
    <soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">
        <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
            <wsu:Timestamp wsu:Id="TS-%(identifier)s">
                <wsu:Created>%(Created)s</wsu:Created>
                <wsu:Expires>%(Expires)s</wsu:Expires>
            </wsu:Timestamp>
            <wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="BAKENDEVS-%(identifierSecurityToken)s">%(Certificate)s</wsse:BinarySecurityToken>
            <ds:Signature Id="SIG-%(identifier)s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="wsa soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                    </ds:CanonicalizationMethod>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="#ID-%(identifierTo)s">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                                <ec:InclusiveNamespaces PrefixList="soap wcf" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </ds:Transform>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue></ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue></ds:SignatureValue>
                <ds:KeyInfo Id="KI-%(identifier)s">
                    <wsse:SecurityTokenReference wsu:Id="STR-%(identifier)s">
                        <wsse:Reference URI="#BAKENDEVS-%(identifierSecurityToken)s" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"/>
                    </wsse:SecurityTokenReference>
                </ds:KeyInfo>
            </ds:Signature>
        </wsse:Security>
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendBillSync</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:SendBillSync>
            <wcf:fileName>%(fileName)s</wcf:fileName>
            <wcf:contentFile>%(contentFile)s</wcf:contentFile>
        </wcf:SendBillSync>
    </soap:Body>
</soap:Envelope>
"""
        return template_SendBillSyncsend_xml

            # <wcf:testSetId>%(testSetId)s</wcf:testSetId>

    @api.model
    def _generate_SendBillSync_send_xml(self, template_send_data_xml, fileName, contentFile, Created, 
        testSetId, identifier, Expires, Certificate, identifierSecurityToken, identifierTo):
        data_send_xml = template_send_data_xml % {
                        'fileName' : fileName,
                        'contentFile' : contentFile,
                        'testSetId' : testSetId,
                        'identifier' : identifier,
                        'Created' : Created,
                        'Expires' : Expires,
                        'Certificate' : Certificate,
                        'identifierSecurityToken' : identifierSecurityToken,
                        'identifierTo' : identifierTo,
                        }
        return data_send_xml


    def _get_datetime(self):
        fmt = "%Y-%m-%d %H:%M:%S"
        date_time_envio = datetime.now(timezone('UTC'))
        date_time_envio = date_time_envio + timedelta(hours=-5)     
        date_time_envio = date_time_envio.strftime(fmt) 
        return date_time_envio


    def _cron_validate_accept_email_invoice_dian(self):
        date_current = self._get_datetime()  
        date_current = datetime.strptime(date_current, '%Y-%m-%d %H:%M:%S')
        rec_dian_documents = self.env['dian.document'].sudo().search([('state','=','exitoso'),('email_response','=','pending')])
        for rec_dian_document in rec_dian_documents:
            if rec_dian_document.date_email_send:
                time_difference = date_current - rec_dian_document.date_email_send 
                if time_difference.days > 3:
                    rec_dian_document.date_email_acknowledgment = fields.Datetime.now()
                    rec_dian_document.email_response = 'accepted'


    def _get_rate_date(self, company_id, currency_id, date_invoice):
        Calculationrate = 0.00
        sql = '''
        select max(name) as date
          from res_currency_rate
         where company_id = %s
           and currency_id = %s
           and name <= '%s'
         ''' % (company_id, currency_id, date_invoice)

        self.sudo().env.cr.execute( sql )
        resultado = self.sudo().env.cr.dictfetchall()
        if  resultado[0]['date'] != None:
            sql = '''
            select rate as rate
              from res_currency_rate
             where company_id = %s
               and currency_id = %s
               and name = '%s'
             ''' % (company_id, currency_id, resultado[0]['date'])

            self.sudo().env.cr.execute( sql )
            resultado = self.sudo().env.cr.dictfetchall()
            rate = resultado[0]['rate']
            Calculationrate = 1.00 / rate
        else:
            raise ValidationError("La divisa utilizada en la factura no tiene tasa de cambio registrada")
        return Calculationrate


    def generate_attachment_document(self, invoice, dian_document):
        #self.exist_dian( dian_document.id )
        #'08828b44-2e44-4f62-b445-79b999947bfa'

        '''self.exist_dian( dian_document.id )

        headers = {'content-type': 'application/soap+xml'}
        data_xml_send = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap‐envelope" xmlns:wcf="http:/wcf.dian.colombia">
        <soap:Header><wsse:Security xmlns:wsse="http:/docs.oasis‐open.org/wss/2004/01/oasis‐200401‐wss‐wssecurity‐secext‐1.0.xsd" xmlns:wsu="http:/docs.oasis‐open.org/wss/2004/01/oasis‐200401‐wss‐
        wssecurity‐utility‐1.0.xsd"/></soap:Header>
        <soap:Body>
        <wcf:GetStatus
        <wcf:trackId>73e40b3a-35b3-4fdc-8d3d-560f045bd439</wcf:trackId>
        </wcf:GetStatus>
        </soap:Body>
        </soap:Envelope>"""

        parser = etree.XMLParser(remove_blank_text=True)
        data_xml_send = etree.tostring(etree.XML(data_xml_send, parser=parser))
        data_xml_send = data_xml_send.decode()

        response = requests.post('https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?wsdl', data=data_xml_send, headers=headers)'''


        dian_constants = self._get_dian_constants(invoice)
        xml = self.get_xml_template_attachment_document( )

        data_constants_document = self._generate_data_constants_document(invoice, dian_constants, invoice.type,invoice.company_id.in_contingency_4)

        now_utc = datetime.now(timezone('UTC'))
        now_bogota = now_utc
        issue_date = now_bogota.strftime("%Y-%m-%d")

        dian_constants.update({
            'AttachedDocumentID' : random.getrandbits(128),
            'IssueDate' : issue_date,
            'IssueTime' : self._get_time_colombia(),
            'ParentDocumentID' : invoice.number,
            'CustomerTaxLevelCode' : self._get_partner_fiscal_responsability_code(invoice.partner_id.id),
            'SupplierTaxLevelCode' : self._get_partner_fiscal_responsability_code(invoice.company_id.partner_id.id),
            'CustomerRegistrationName' : data_constants_document.get('CustomerRegistrationName'),
            'CustomerShemeID' : data_constants_document.get('CustomerShemeID'),
            'CustomerShemeName' : data_constants_document.get('CustomerShemeName'),
            'CustomerShemeName' : data_constants_document.get('CustomerShemeName'),
            'TaxSchemeID' : data_constants_document.get('TaxSchemeID'),
            'TaxSchemeName' : data_constants_document.get('TaxSchemeName'),
            'CustomerID' : data_constants_document.get('CustomerID'),
            'InvoiceXML' : dian_document.xml_document,
            'Cufe' : invoice.cufe
        })

        xml = xml % dian_constants

        raise UserError(xml)


    def get_xml_template_attachment_document(self):
        # pag 43 muestra los diversos documentos
        # pag 636
        # 144 posiblemente donde esta la respuesta XmlBase64Bytes
        res = """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <AttachedDocument
            xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns="urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2">
            <cbc:UBLVersionID>%(UBLVersionID)s</cbc:UBLVersionID>
            <cbc:CustomizationID>Documentos adjuntos</cbc:CustomizationID>
            <cbc:ProfileID>%(ProfileID)s</cbc:ProfileID>
            <cbc:ProfileExecutionID>%(ProfileExecutionID)s</cbc:ProfileExecutionID>
            <cbc:ID>%(AttachedDocumentID)s</cbc:ID>
            <cbc:IssueDate>%(IssueDate)s</cbc:IssueDate>
            <cbc:IssueTime>%(IssueTime)s</cbc:IssueTime>
            <cbc:DocumentType>Contenedor de Factura Electrónica</cbc:DocumentType>
            <cbc:ParentDocumentID>%(ParentDocumentID)s</cbc:ParentDocumentID>
            <cac:SenderParty>
                <cac:PartyTaxScheme>
                    <cbc:RegistrationName>%(SupplierPartyName)s</cbc:RegistrationName>
                    <cbc:CompanyID schemeAgencyID="195" schemeID="%(schemeID)s" schemeName="%(SupplierSchemeID)s">%(SupplierID)s</cbc:CompanyID>
                    <cbc:TaxLevelCode listName="48">%(SupplierTaxLevelCode)s</cbc:TaxLevelCode>
                    <cac:TaxScheme>
                        <cbc:ID>%(TaxSchemeID)s</cbc:ID>
                        <cbc:Name>%(TaxSchemeName)s</cbc:Name>
                    </cac:TaxScheme>
                </cac:PartyTaxScheme>
            </cac:SenderParty>
            <cac:ReceiverParty>
                <cac:PartyTaxScheme>
                    <cbc:RegistrationName>%(CustomerRegistrationName)s</cbc:RegistrationName>
                    <cbc:CompanyID schemeAgencyID="195" schemeID="%(CustomerShemeID)s" schemeName="%(CustomerShemeName)s">%(CustomerID)s</cbc:CompanyID>
                    <cbc:TaxLevelCode listName="48">%(CustomerTaxLevelCode)s</cbc:TaxLevelCode>
                    <cac:TaxScheme>
                        <cbc:ID>%(TaxSchemeID)s</cbc:ID>
                        <cbc:Name>%(TaxSchemeName)s</cbc:Name>
                    </cac:TaxScheme>
                </cac:PartyTaxScheme>
            </cac:ReceiverParty>
            <cac:Attachment>
                <cac:ExternalReference>
                    <cbc:MimeCode>text/xml</cbc:MimeCode>
                    <cbc:EncodingCode>UTF-8</cbc:EncodingCode>
                    <cbc:Description>%(InvoiceXML)s</cbc:Description>
                </cac:ExternalReference>
            </cac:Attachment>
            <cac:ParentDocumentLineReference>
                <cbc:LineID>1</cbc:LineID>
                <cac:DocumentReference>
                    <cbc:ID>%(ParentDocumentID)s</cbc:ID>
                    <cbc:UUID schemeName="CUFE-SHA384">%(Cufe)s</cbc:UUID>
                    <cbc:IssueDate>2021-05-10</cbc:IssueDate>
                    <cbc:DocumentType>ApplicationResponse</cbc:DocumentType>
                    <cac:Attachment>
                        <cac:ExternalReference>
                            <cbc:MimeCode>text/xml</cbc:MimeCode>
                            <cbc:EncodingCode>UTF-8</cbc:EncodingCode>
                            <cbc:Description>
                                <![CDATA[<?xml version="1.0" encoding="utf-8" standalone="no"?>]]>
                            </cbc:Description>
                        </cac:ExternalReference>
                    </cac:Attachment>
                    <cac:ResultOfVerification>
                        <cbc:ValidatorID>Unidad Especial Dirección de Impuestos y Aduanas Nacionales</cbc:ValidatorID>
                        <cbc:ValidationResultCode>02</cbc:ValidationResultCode>
                        <cbc:ValidationDate>2021-05-10</cbc:ValidationDate>
                        <cbc:ValidationTime>17:20:11-05:00</cbc:ValidationTime>
                    </cac:ResultOfVerification>
                </cac:DocumentReference>
            </cac:ParentDocumentLineReference>
        </AttachedDocument>                            
        
        """

        return res

