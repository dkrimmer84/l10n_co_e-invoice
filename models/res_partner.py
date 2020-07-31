# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date

class ResPartner(models.Model):
    _inherit = 'res.partner'
    _name = 'res.partner'

    tribute_id = fields.Many2one('dian.tributes', string="Tributos", required = False)
    fiscal_responsability_ids = fields.Many2many('dian.fiscal.responsability', string="Responsabilidad fiscal", required = False)
    is_foreign = fields.Char('Is foreign')    


    @api.onchange('x_name1', 'x_name2', 'x_lastname1', 'x_lastname2', 'companyName',
                  'pos_name', 'companyBrandName')
    def _concat_name(self):
        """
        This function concatenates the four name fields in order to be able to
        search for the entire name. On the other hand the original name field
        should not be editable anymore as the new name fields should fill it up
        automatically.
        @return: void
        """
        # Avoiding that "False" will be written into the name field
        if self.x_name1 is False:
            self.x_name1 = ''

        if self.x_name2 is False:
            self.x_name2 = ''

        if self.x_lastname1 is False:
            self.x_lastname1 = ''

        if self.x_lastname2 is False:
            self.x_lastname2 = ''

        # Collecting all names in a field that will be concatenated
        nameList = [
            self.x_name1,
            self.x_name2,
            self.x_lastname1,
            self.x_lastname2
        ]

        formatedList = []
        if self.companyName is False:
            if self.type == 'delivery':
                self.name = self.pos_name
                self.x_name1 = False
                self.x_name2 = False
                self.x_lastname1 = False
                self.x_lastname2 = False
                self.doctype = 1
            else:
                for item in nameList:
                    if item is not '':
                        formatedList.append(item)
                self.name = ' ' .join(formatedList)
        else:
            # Some Companies are know for their Brand, which could conflict from the users point of view while
            # searching the company (e.j. o2 = brand, Telefonica = Company)
            if self.companyBrandName is not False:
                delimiter = ', '
                company_list = (self.companyBrandName, self.companyName)
                self.name = delimiter.join(company_list)
            else:
                self.name = self.companyName    


    @api.onchange('x_name1')
    def onChangeNameUpper(self):
        """
        Permite que cuando se termine de escribir se pueda pasar el campo
        x_name1 automaticamente a mayuscula
        @return: void
        """
        if self.x_name1 is not False:
            self.x_name1 = self.x_name1

    @api.onchange('x_name2')
    def onChangeName2Upper(self):
        """
        Permite que cuando se termine de escribir se pueda pasar el campo
        x_name2 automaticamente a mayuscula
        @return: void
        """
        if self.x_name2 is not False:
            self.x_name2 = self.x_name2             

    @api.onchange('x_lastname1')
    def onChangeLastNameUpper(self):
        """
        Permite que cuando se termine de escribir se pueda pasar el campo
        x_lastname1 automaticamente a mayuscula
        @return: void
        """
        if self.x_lastname1 is not False:
            self.x_lastname1 = self.x_lastname1


    @api.onchange('x_lastname2')
    def onChangeLastName2Upper(self):
        """
        Permite que cuando se termine de escribir se pueda pasar el campo
        x_lastname2 automaticamente a mayuscula
        @return: void
        """
        if self.x_lastname2 is not False:
            self.x_lastname2 = self.x_lastname2


                        
    @api.onchange('companyName')
    def onChangeCompanyNUpper(self):
        """
        Permite que cuando se termine de escribir se pueda pasar el campo
        companyName automaticamente a mayuscula
        @return: void
        """
        if self.companyName is not False:
            self.companyName = self.companyName
