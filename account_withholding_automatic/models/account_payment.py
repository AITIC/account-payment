##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
# import odoo.addons.decimal_precision as dp
# from odoo.exceptions import ValidationError
# from dateutil.relativedelta import relativedelta
# import datetime


class AccountPayment(models.Model):
    _inherit = "account.payment"

    automatic = fields.Boolean(
    )
    withholding_accumulated_payments = fields.Selection(
        related='tax_withholding_id.withholding_accumulated_payments',
    )
    withholdable_invoiced_amount = fields.Float(
        'Importe imputado sujeto a retencion',
        # compute='get_withholding_data',
        readonly=True,
    )
    withholdable_advanced_amount = fields.Float(
        'Importe a cuenta sujeto a retencion',
        # compute='get_withholding_data',
        readonly=True,
    )
    accumulated_amount = fields.Float(
        # compute='get_withholding_data',
        readonly=True,
    )
    total_amount = fields.Float(
        # compute='get_withholding_data',
        readonly=True,
    )
    withholding_non_taxable_minimum = fields.Float(
        'Non-taxable Minimum',
        # compute='get_withholding_data',
        readonly=True,
    )
    withholding_non_taxable_amount = fields.Float(
        'Non-taxable Amount',
        # compute='get_withholding_data',
        readonly=True,
    )
    withholdable_base_amount = fields.Float(
        # compute='get_withholding_data',
        readonly=True,
    )
    period_withholding_amount = fields.Float(
        # compute='get_withholding_data',
        readonly=True,
    )
    previous_withholding_amount = fields.Float(
        # compute='get_withholding_data',
        readonly=True,
    )
    computed_withholding_amount = fields.Float(
        # compute='get_withholding_data',
        readonly=True,
    )

    def _get_counterpart_move_line_vals(self, invoice=False):
        vals = super(AccountPayment, self)._get_counterpart_move_line_vals(
            invoice=invoice)
        if self.payment_group_id:
            # we check they are code withholding and we get taxes
            taxes = self.payment_group_id.payment_ids.filtered(
                lambda x: x.payment_method_code == 'withholding').mapped(
                'tax_withholding_id')
            vals['tax_ids'] = [(6, False, taxes.ids)]
        return vals

    @api.onchange('payment_method_code')
    def onchange_tax_withholding_id(self):
        if self.payment_method_code == 'withholding' and not self.tax_withholding_id and \
                self.journal_id.withholding_account_tag_ids and self.payment_type in ['inbound', 'outbound']:
            if (
                    (self.partner_type == 'customer' and
                        self.payment_type == 'inbound') or
                    (self.partner_type == 'supplier' and
                        self.payment_type == 'outbound')):
                rep_field = 'invoice_repartition_line_ids'
            else:
                rep_field = 'refund_repartition_line_ids'
            tax_ids = self.env['account.tax'].search([('type_tax_use', '=', self.partner_type),
                                              ('company_id', '=', self.company_id.id)])
            tax_withholding_ids = tax_ids[rep_field].filtered(lambda x: x.repartition_type == 'tax' and \
                                                             x.mapped('tag_ids') & \
                                                             self.journal_id.withholding_account_tag_ids).mapped('tax_id')
            if tax_withholding_ids:
                self.tax_withholding_id = tax_withholding_ids[0]
