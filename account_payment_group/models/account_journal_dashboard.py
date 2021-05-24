from odoo import models

import ast


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def open_payments_action(self, payment_type, mode='tree'):
        if payment_type == 'transfer':
            action_rec = self.env['ir.model.data'].xmlid_to_object(
                'account_payment_group.action_account_payments_transfer')
            action = action_rec.read([])[0]
            action['context'] = dict(ast.literal_eval(action.get('context')), default_journal_id=self.id,
                                     search_default_journal_id=self.id)
            action['context'].update({
                'default_partner_id': self.company_id.partner_id.id,
                'default_is_internal_transfer': True,
            })
            action['domain'] = [('is_internal_transfer', '=', True)]
            if mode == 'form':
                action['views'] = [[False, 'form']]
            return action
        return super(AccountJournal, self).open_payments_action(payment_type, mode=mode)
