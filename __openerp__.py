# -*- coding: utf-8 -*-

{
    'name': "Colombian e-invoice",

    'summary': """
        genera la facturacion electronica para la distribucion colombiana segun requisitos de la DIAN""",
    'category': 'Administration',
    'version': '9.0',
    'depends': [
        'account',
    ],
    'data': ['views/dian_view.xml','views/company_view.xml','views/invoice_view.xml']
}
