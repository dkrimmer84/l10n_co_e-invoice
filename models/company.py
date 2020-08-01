# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from datetime import datetime, timedelta, date
from pytz import timezone
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

try:
    import xmltodict
except ImportError:
    _logger.warning('Cannot import xmltodict library')

try:
    import requests 
except:    
    _logger.warning("no se ha cargado requests")

try:
    import uuid
except ImportError:
    _logger.warning('Cannot import uuid library')

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    import OpenSSL
    from OpenSSL import crypto
    type_ = crypto.FILETYPE_PEM
except:
    _logger.warning('Cannot import OpenSSL library')

try:
    from lxml import etree
except:
    print("Cannot import  etree **********************************************")

try:
    import hashlib
except ImportError:
    _logger.warning('Cannot import hashlib library ***********************')

try:
    import base64
except ImportError:
    _logger.warning('Cannot import base64 library ***********************')

server_url = {
    'HABILITACION':'https://facturaelectronica.dian.gov.co/habilitacion/B2BIntegrationEngine/FacturaElectronica/facturaElectronica.wsdl',
    'PRODUCCION':'https://facturaelectronica.dian.gov.co/operacion/B2BIntegrationEngine/FacturaElectronica/facturaElectronica.wsdl',
    'HABILITACION_CONSULTA':'https://facturaelectronica.dian.gov.co/habilitacion/B2BIntegrationEngine/FacturaElectronica/consultaDocumentos.wsdl',
    'PRODUCCION_CONSULTA':'https://facturaelectronica.dian.gov.co/operacion/B2BIntegrationEngine/FacturaElectronica/consultaDocumentos.wsdl',
    'PRODUCCION_VP':'https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?wsdl',                      
    'HABILITACION_VP':'https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl'
}

class Company(models.Model):
    _inherit = 'res.company'
    _name = 'res.company'


    def _get_dian_sequence(self):
        list_dian_sequence = []
        rec_dian_sequence = self.env['ir.sequence'].search([('company_id', '=', self.env.user.partner_id.company_id.id), ('use_dian_control', '=', True),('active', '=', True)])
        for sequence in rec_dian_sequence:
            list_dian_sequence.append((str(sequence.id), sequence.name))
        return list_dian_sequence


    trade_name = fields.Char(string="Razón social", required=True, default="")
    digital_certificate = fields.Text(string="Certificado digital público", required=True, default="")
    software_identification_code = fields.Char(string="Código de identificación del software", required=True, default="")
    identificador_set_pruebas = fields.Char(string = 'Identificador del SET de pruebas', required = True ) 
    
    software_pin = fields.Char(string="PIN del software", required=True, default="")
    password_environment = fields.Char(string="Clave de ambiente", required=True, default="")
    seed_code = fields.Integer(string="Código de semilla", required=True, default=5000000)
    issuer_name = fields.Char(string="Ente emisor del certificado", required=True, default="")
    serial_number = fields.Char(string="Serial del certificado", required=True, default="")
    document_repository = fields.Char(string='Ruta de almacenamiento de archivos', required=True)
    in_use_dian_sequence = fields.Selection('_get_dian_sequence', 'Secuenciador DIAN a utilizar', required=False)
    certificate_key = fields.Char(string='Clave del certificado P12', required=True, default="")
    operation_type = fields.Selection([('01','Combustible'),('02','Emisor es Autoretenedor'),('03','Excluidos y Exentos'),
    ('04','Exportación'),('05','Generica'),('06','Generica con pago anticipado'),
    ('07','Generica con periodo de facturacion'),('08','Consorcio'),('09','AIU'),('10','Estandar *'),
    ('11','Mandatos'),('12','Mandatos Servicios')], string='Tipo de operación DIAN', required=True)
    pem = fields.Char(string="Nombre del archivo PEM del certificado", required=True, default="")
    certificate = fields.Char(string="Nombre del archivo del certificado", required=True, default="")
    production = fields.Boolean(string='Pase a producción', default=False)
    xml_response_numbering_range = fields.Text(string='Contenido XML de la respuesta DIAN a la consulta de rangos', readonly=True)
    in_contingency_4 = fields.Boolean(string="En contingencia", default=False)
    date_init_contingency_4 = fields.Datetime(string='Fecha de inicio de contingencia 4')
    date_end_contingency_4 = fields.Datetime(string='Fecha de fin de contingencia 4')
    exists_invoice_contingency_4 = fields.Boolean(string="Cantidad de facturas con contingencia 4 sin reportar a la DIAN", default=False)


    def query_numbering_range(self):
        identifier = uuid.uuid4()
        identifierTo = uuid.uuid4()
        identifierSecurityToken = uuid.uuid4()
        timestamp = self._generate_datetime_timestamp()
        Created = timestamp['Created']
        Expires = timestamp['Expires']
        Certificate = self.digital_certificate
        ProviderID = self.partner_id.xidentification
        SoftwareID = self.software_identification_code
        template_GetNumberingRange_xml = self._template_GetNumberingRange_xml()
        data_xml_send = self._generate_GetNumberingRange_send_xml(template_GetNumberingRange_xml, 
            identifier, Created, Expires, Certificate, ProviderID, ProviderID, 
            SoftwareID, identifierSecurityToken, identifierTo)

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
        
        document_repository = self.document_repository
        archivo_pem = self.pem
        archivo_certificado = self.certificate
        password = self.certificate_key

        SignatureValue = self._generate_SignatureValue_GetNumberingRange(document_repository, password, Signedinfo, archivo_pem, archivo_certificado)
        data_xml_send = data_xml_send.replace('<ds:SignatureValue/>','<ds:SignatureValue>%s</ds:SignatureValue>' % SignatureValue)
        headers = {'content-type': 'application/soap+xml'}
        if self.production:
            try:
                response = requests.post(server_url['PRODUCCION_VP'],data=data_xml_send,headers=headers)
            except:
                raise ValidationError('No existe comunicación con la DIAN para el servicio de consulta de rangos de numeración')
        else:
            try:
                response = requests.post(server_url['HABILITACION_VP'],data=data_xml_send,headers=headers)
            except:
                raise ValidationError('No existe comunicación con la DIAN para el servicio de consulta de rangos de numeración')
        #   Respuesta de petición
        if response.status_code != 200: # Respuesta de envío no exitosa
            if response.status_code == 500:
                raise ValidationError('Error 500 = Error de servidor interno')
            if response.status_code == 503:
                raise ValidationError('Error 503 = Servicio no disponible')
        #   Procesa respuesta DIAN 
        response_dict = xmltodict.parse(response.content)
        self.xml_response_numbering_range = response.content


    @api.multi
    def _generate_SignatureValue_GetNumberingRange(self, document_repository, password, data_xml_SignedInfo_generate, archivo_pem, archivo_certificado):
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


    def _generate_digestvalue_to(self, elementTo):
        # Generar el digestvalue de to
        elementTo = etree.tostring(etree.fromstring(elementTo), method="c14n")
        elementTo_sha256 = hashlib.new('sha256', elementTo)
        elementTo_digest = elementTo_sha256.digest()
        elementTo_base = base64.b64encode(elementTo_digest)
        elementTo_base = elementTo_base.decode()
        return elementTo_base


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


    def _template_GetNumberingRange_xml(self):
        template_GetNumberingRange_xml = """
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
        <wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/GetNumberingRange</wsa:Action>
        <wsa:To wsu:Id="ID-%(identifierTo)s" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">https://vpfe.dian.gov.co/WcfDianCustomerServices.svc</wsa:To>
    </soap:Header>
    <soap:Body>
        <wcf:GetNumberingRange>
            <wcf:accountCode>%(accountCode)s</wcf:accountCode>
            <wcf:accountCodeT>%(accountCodeT)s</wcf:accountCodeT>
            <wcf:softwareCode>%(softwareCode)s</wcf:softwareCode>
        </wcf:GetNumberingRange>
    </soap:Body>
</soap:Envelope>
"""
        return template_GetNumberingRange_xml


    @api.model
    def _generate_GetNumberingRange_send_xml(self, template_getstatus_send_data_xml, identifier, Created, 
        Expires,  Certificate, accountCode, accountCodeT, softwareCode, 
        identifierSecurityToken, identifierTo):
        data_consult_numbering_range_send_xml = template_getstatus_send_data_xml % {
                        'identifier' : identifier,
                        'Created' : Created,
                        'Expires' : Expires,
                        'Certificate' : Certificate,
                        'accountCode' : accountCode,
                        'accountCodeT' : accountCodeT,
                        'softwareCode' : softwareCode,
                        'identifierSecurityToken' : identifierSecurityToken,
                        'identifierTo' : identifierTo,
                    }
        return data_consult_numbering_range_send_xml
