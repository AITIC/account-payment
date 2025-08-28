##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountPaymentGroup(models.Model):
    _inherit = 'account.payment.group'

    cashbox_session_id = fields.Many2one(
        'account.cashbox.session',
        string='POP Session',
        readonly=True,
        store=True
    )

    cashbox_filter = fields.Binary(string='Cashbox Filter', compute="_compute_cashbox_payment_method_ids", readonly=True)
    cashbox_payment_method_ids = fields.Many2many('account.journal', compute="_compute_cashbox_payment_method_ids", string="Payment Methods", readonly=True)
    amount_display = fields.Monetary(string=_('Display Amount'), currency_field='currency_id', store=True)

    @api.depends('account_payment_id')
    def _compute_cashbox_payment_method_ids(self):
        for rec in self:
            payment_id = self.env['account.payment'].browse(self.env.context.get('payment_id'))
            if payment_id.cashbox_session_id:
                rec.cashbox_payment_method_ids = payment_id.cashbox_payment_method_ids
                rec.cashbox_filter = payment_id.cashbox_filter
                rec.journal_id = payment_id.cashbox_session_id.cashbox_id.journal_ids[:1].id if payment_id.cashbox_session_id.cashbox_id.journal_ids else False
                _logger.info(f"cashbox filter {rec.cashbox_filter}")
            else:
                if rec.currency_id != rec.company_id.currency_id:
                    journal_ids = self.env['account.journal'].search([
                        ('type', 'in', ['bank','cash']),
                        ('default_account_payment_group','=',False),
                        ('currency_id','=',rec.currency_id.id)
                    ])
                else:
                    journal_ids = self.env['account.journal'].search([
                        ('type', 'in', ['bank','cash']),
                        ('default_account_payment_group','=',False),
                        ('currency_id','=',False)
                    ])
                rec.cashbox_filter = [('id','in',journal_ids.ids)] 
                rec.cashbox_payment_method_ids = False
