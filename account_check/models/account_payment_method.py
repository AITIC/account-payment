from odoo import models, api, _
import logging
_logger = logging.getLogger(__name__)


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['received_third_check'] = {'mode': 'multi', 'domain': [('type', '=', 'cash')]}
        res['delivered_third_check'] = {'mode': 'multi', 'domain': [('type', '=', 'cash')]}
        res['issue_check'] = {'mode': 'multi', 'domain': [('type', '=', 'cash')]}
        return res
