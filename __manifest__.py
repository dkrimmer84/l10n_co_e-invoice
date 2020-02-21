# -*- coding: utf-8 -*-

{
    'name': "Colombian e-invoice",

    'summary': """
        genera la facturacion electronica para la distribucion colombiana segun requisitos de la DIAN""",
    'category': 'Administration',
    'version': '10.0',
    'depends': [
        'account', 'l10n_co_tax_extension', 'base', 'contacts'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/dian_fiscal_responsability_data.xml',
        'data/dian_tributes_data.xml',
        'data/sequence.xml',
        'views/dian_view.xml',
        'views/company_view.xml',
        'views/invoice_view.xml',
        'views/res_partner_view.xml',
        'views/report_invoice.xml',
        'views/account_view.xml',
        'views/sequence_view.xml',
        'views/product_view.xml',
        'views/l10n_cities_co_view.xml'
    ],

    'installable' : True
}
