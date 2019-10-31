{
    'name': "Colombian e-invoice",
    'summary': """
        genera la facturacion electronica para la distribucion colombiana segun requisitos de la DIAN""",
    'category': 'Administration',
    'version': '12.0.0.0.1',
    'depends': [
        'account',
        'l10n_co_tax_extension',
    ],
    'data': [
        'views/report_dian_document.xml',
        'views/dian_view.xml',
        'views/company_view.xml',
        'views/invoice_view.xml',
        'views/sequence_view.xml',
    ],

    'installable' : True
}
