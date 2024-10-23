##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPaymentGroup(models.Model):
    _inherit = 'account.payment.group'

    cashbox_session_id = fields.Many2one(
        'account.cashbox.session',
        string='POP Session',
        related="account_payment_id.cashbox_session_id",
        readonly=True,
        store=True
    )