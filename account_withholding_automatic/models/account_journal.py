from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # Empleamos etiquetas para identificar que diario utilizar para cada tipo de retencion
    #  en caso de que la empresa lo desee.
    withholding_account_tag_ids = fields.Many2many(
        'account.account.tag',
        'account_journal_withholding_account_tag',
        auto_join=True,
        string='Tags for withholding',
        help='Tax labels can be chosen:\n'
        '* To obtain the journal that you want to use to record the withholding.'
    )

    withholding_journal = fields.Boolean(
        compute='_compute_withholding_journal',
    )

    @api.depends('inbound_payment_method_ids', 'outbound_payment_method_ids')
    def _compute_withholding_journal(self):
        payment_out_method = self.env.ref(
            'account_withholding.'
            'account_payment_method_out_withholding')
        payment_in_method = self.env.ref(
            'account_withholding.'
            'account_payment_method_in_withholding')
        for rec in self:
            rec.withholding_journal = False
            if payment_in_method in rec.inbound_payment_method_ids or \
                    payment_out_method in rec.outbound_payment_method_ids:
                rec.withholding_journal = True

