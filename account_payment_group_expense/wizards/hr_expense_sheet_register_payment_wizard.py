from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        """ Update context in order to identify when a account.payment is
        created from an expense.
        """
        return super(
            AccountPaymentRegister,
            self.with_context(create_from_expense=True)
        )._create_payments()
