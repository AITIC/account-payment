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

    @api.depends('account_payment_id')
    def _compute_cashbox_payment_method_ids(self):
        for rec in self:
            rec.cashbox_payment_method_ids = rec.account_payment_id.cashbox_payment_method_ids
            rec.cashbox_filter = rec.account_payment_id.cashbox_filter