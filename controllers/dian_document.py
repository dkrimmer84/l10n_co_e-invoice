# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request
from openerp import fields
import ast
import base64
import logging
import unicodedata
import werkzeug.utils
_logger = logging.getLogger(__name__)


class Main(http.Controller):
 
    @http.route("/l10n_co_e-invoice/accept_dian_invoice", type='http', auth='none', csrf=False)
    def accept_dian_invoice(self, dian_document):
        rec_dian_document = request.env['dian.document'].sudo().search([('cufe','=', dian_document)])
        if not rec_dian_document:
            return u'<html><body><h2>Este documento no existe</h2></body></html>'
        if rec_dian_document.date_email_acknowledgment:
            response = 'aceptado' if rec_dian_document.email_response == 'accepted' else 'rechazado'
            return u'<html><body><h2>Este documento ya fue %s en fecha %s </h2></body></html>' % (response, rec_dian_document.date_email_acknowledgment)
        else:
            rec_dian_document.date_email_acknowledgment = fields.Datetime.now()
            rec_dian_document.email_response = 'accepted'
            accepted_form  = u'''
            <html>
                <body><h2>Se registró satisfactoriamente su decisión</h2></body>
            </html>''' 
        return accepted_form


    @http.route("/l10n_co_e-invoice/reject_dian_invoice", type='http', auth='none', csrf=False)
    def reject_dian_invoice(self, dian_document):
        #rec_dian_document = request.env['dian.document'].sudo().browse(int(dian_document))
        rec_dian_document = request.env['dian.document'].sudo().search([('cufe','=', dian_document)])
        if not rec_dian_document:
            return u'<html><body><h2>Este documento no existe</h2></body></html>'
        if rec_dian_document.date_email_acknowledgment:
            response = 'aceptado' if rec_dian_document.email_response == 'accepted' else 'rechazado'
            return u'<html><body><h2>Este documento ya fue %s en fecha %s </h2></body></html>' % (response, rec_dian_document.date_email_acknowledgment)
        else:
            reject_reason_form = u'''
            <html>
                <body>
                    <form action="/l10n_co_e-invoice/reject_dian_invoice_reason">
                        <table>
                            <tr><th><b>Rechazo de documento DIAN</b></th></tr>
                            <tr><td></td></tr>
                            <tr><td><input type="hidden" name="dian_document" value=%s>
                            <b>Ingresa tú observación:</b></td></tr>
                            <tr><td><textarea rows="6" cols=80 name="reason"></textarea></td></tr>
                            <tr><td><input type="submit" value="Rechazar"></td></tr>
                        </table>
                    </form>
                </body>
            </html>''' % dian_document
            return reject_reason_form


    @http.route("/l10n_co_e-invoice/reject_dian_invoice_reason", type='http', auth='none', csrf=False)
    def reject_dian_invoice_reason(self, dian_document, reason):
        rec_dian_document = request.env['dian.document'].sudo().search([('cufe','=', dian_document)])
        if not rec_dian_document:
            return u'<html><body><h2>Este documento no existe</h2></body></html>'
        if rec_dian_document.date_email_acknowledgment:
            response = 'aceptado' if rec_dian_document.email_response == 'accepted' else 'rechazado'
            return u'<html><body><h2>Este documento ya fue %s en fecha %s </h2></body></html>' % (response, rec_dian_document.date_email_acknowledgment)
        if not reason:
            reject_reason_form = u'''
            <html>
                <body>
                    <form action="/l10n_co_e-invoice/reject_dian_invoice_reason">
                        <table>
                            <tr><th><b>Rechazo de documento DIAN</b></th></tr>
                            <tr><td></td></tr>
                            <tr><td><input type="hidden" name="dian_document" value=%s>
                            <b>Ingresa tú observación:</b></td></tr>
                            <tr><td><textarea rows="6" cols=80 name="reason">Debe ingresar una observación</textarea></td></tr>
                            <tr><td><input type="submit" value="Rechazar"></td></tr>
                        </table>
                    </form>
                </body>
            </html>'''  % dian_document
        else:
            rec_dian_document = request.env['dian.document'].sudo().search([('cufe','=', dian_document)])
            rec_dian_document.date_email_acknowledgment = fields.Datetime.now()
            rec_dian_document.email_response = 'rejected'
            rec_dian_document.email_reject_reason = reason
            reject_reason_form  = u'''
            <html>
                <body><h2>Se registró satisfactoriamente su decisión</h2></body>
            </html>'''
            return reject_reason_form