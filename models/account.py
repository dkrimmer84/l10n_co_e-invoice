# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountTax(models.Model):
    _inherit = 'account.tax'
    _name = 'account.tax'

    tax_group_fe = fields.Selection([('iva_fe','IVA FE'), ('ica_fe','ICA FE'), ('ico_fe','INC FE'), ('ret_fe','RET FE'), ('nap_fe','No palica a DIAN FE')], 
        string="Grupo de impuesto DIAN FE", default='nap_fe')
    tributes = fields.Selection([('01','IVA'), ('02','IC'), ('03','ICA'), ('04','INC'), ('05','ReteIVA'), ('06','ReteFuente'),
                            ('07','ReteICA'), ('08','ReteCREE'), ('20','FtoHorticultura'), ('21','Timbre'),
                            ('22','Bolsas'), ('23','INCarbono'), ('24','INCombustibles'),
                            ('25','Sobretasa Combustibles'), ('26','Sordicom'),
                            ('ZY','No causa'),
                            ('ZZ','Nombre de la figura tributaria')
                    ],string="Tributo DIAN")


class AccountJournal(models.Model):
    _inherit = "account.journal"

    debit_note_sequence_id = fields.Many2one('ir.sequence', string='Debit Note Entry Sequence',
        help="This field contains the information related to the numbering of the dedit note entries of this journal.", copy=False)

    debit_note_sequence_number_next = fields.Integer(string='Nota de débito: Número siguiente',
        help='The next sequence number will be used for the next dedit note.',
        compute='_compute_debit_note_seq_number_next',
        inverse='_inverse_debit_note_seq_number_next')

    debit_note_sequence = fields.Boolean(string='Dedicated Dedit Note Sequence', help="Check this box if you don't want to share the same sequence for invoices and dedit notes made from this journal", default=False)


    @api.multi
    # do not depend on 'debit_note_sequence_id.date_range_ids', because
    # debit_note_sequence_id._get_current_sequence() may invalidate it!
    @api.depends('debit_note_sequence_id.use_date_range', 'debit_note_sequence_id.number_next_actual')
    def _compute_debit_note_seq_number_next(self):
        '''Compute 'sequence_number_next' according to the current sequence in use,
        an ir.sequence or an ir.sequence.date_range.
        '''
        for journal in self:
            if journal.debit_note_sequence_id and journal.debit_note_sequence:
                sequence = journal.debit_note_sequence_id._get_current_sequence()
                journal.debit_note_sequence_number_next = sequence.number_next_actual
            else:
                journal.debit_note_sequence_number_next = 1

    @api.multi
    def _inverse_debit_note_seq_number_next(self):
        '''Inverse 'debit_note_sequence_number_next' to edit the current sequence next number.
        '''
        for journal in self:
            if journal.debit_note_sequence_id and journal.debit_note_sequence and journal.debit_note_sequence_number_next:
                sequence = journal.debit_note_sequence_id._get_current_sequence()
                sequence.number_next = journal.debit_note_sequence_number_next

    @api.model
    def create(self, vals):
        if vals.get('type') in ('sale', 'purchase') and vals.get('debit_note_sequence') and not vals.get('debit_note_sequence_id'):
            vals.update({'debit_note_sequence_id': self.sudo()._create_sequence_debit_note(vals, debitnote=True).id})
        journal = super(AccountJournal, self).create(vals)
        return journal

    @api.multi
    def write(self, vals):
        # create the relevant debit note sequence
        if vals.get('debit_note_sequence'):
            for journal in self.filtered(lambda j: j.type in ('sale', 'purchase') and not j.debit_note_sequence_id):
                journal_vals = {
                    'name': journal.name,
                    'company_id': journal.company_id.id,
                    'code': journal.code,
                    'debit_note_sequence_number_next': vals.get('debit_note_sequence_number_next', journal.debit_note_sequence_number_next),
                }
                journal.debit_note_sequence_id = self.sudo()._create_sequence_debit_note(journal_vals, debitnote=True).id
        result = super(AccountJournal, self).write(vals)
        return result

    @api.model
    def _create_sequence_debit_note(self, vals, debitnote=False):
        """ Create new no_gap entry sequence for every new Journal"""
        prefix = self._get_sequence_prefix(vals['code'], debitnote)
        seq_name = debitnote and vals['code'] + _(': Debit note') or vals['code']
        seq = {
            'name': _('%s Sequence') % seq_name,
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        seq = self.env['ir.sequence'].create(seq)
        seq_date_range = seq._get_current_sequence()
        seq_date_range.number_next = debitnote and vals.get('debit_note_sequence_number_next', 1) or vals.get('sequence_number_next', 1)
        return seq