# -*- coding: utf-8 -*-

from odoo import fields, models, api
# from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # state = fields.Selection(track_visibility='always')
    amount = fields.Monetary(currency_field='currency_id', track_visibility='always')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer/Vendor",
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        check_company=True,
        track_visibility='always')

    currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=True,
                                  states={'draft': [('readonly', False)]},
                                  string='Currency',
                                  track_visibility='always',
                                  compute=False)

    # amount = fields.Monetary(track_visibility='always')
    # partner_id = fields.Many2one(track_visibility='always')
    # journal_id = fields.Many2one(track_visibility='always')
    # destination_journal_id = fields.Many2one(track_visibility='always')
    # currency_id = fields.Many2one(track_visibility='always')
    # campo a ser extendido y mostrar un nombre detemrinado en las lineas de
    # pago de un payment group o donde se desee (por ej. con cheque, retención,
    # etc)
    payment_method_description = fields.Char(
        compute='_compute_payment_method_description',
        string='Payment Method Desc.',
    )

    def _compute_payment_method_description(self):
        for rec in self:
            rec.payment_method_description = rec.payment_method_id.display_name

    # nuevo campo funcion para definir dominio de los metodos
    payment_method_ids = fields.Many2many(
        'account.payment.method',
        compute='_compute_payment_methods',
        string='Available payment methods',
    )
    journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_journals',
        string='Journals',
    )
    # journal_at_least_type = fields.Char(
    #     compute='_compute_journal_at_least_type'
    # )
    # destination_journal_ids = fields.Many2many(
    #     'account.journal',
    #     compute='_compute_destination_journals'
    # )

    # @api.depends(
    #     # 'payment_type',
    #     'journal_id',
    # )
    # def _compute_destination_journals(self):
    #     for rec in self:
    #         domain = [
    #             ('type', 'in', ('bank', 'cash')),
    #             # al final pensamos mejor no agregar esta restricción, por ej,
    #             # para poder transferir a tarjeta a pagar. Esto solo se usa
    #             # en transferencias
    #             # ('at_least_one_inbound', '=', True),
    #             ('company_id', '=', rec.journal_id.company_id.id),
    #             ('id', '!=', rec.journal_id.id),
    #         ]
    #         rec.destination_journal_ids = rec.journal_ids.search(domain)

    # @api.depends(
    #     'payment_type',
    # )
    # def _compute_journal_at_least_type(self):
    #     for rec in self:
    #         if rec.payment_type == 'inbound':
    #             journal_at_least_type = 'at_least_one_inbound'
    #         else:
    #             journal_at_least_type = 'at_least_one_outbound'
    #         rec.journal_at_least_type = journal_at_least_type
    @api.depends('partner_id', 'destination_account_id', 'journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            payment._compute_partner_id()
            is_partner_ok = payment.partner_id == payment.journal_id.company_id.partner_id
            is_account_ok = payment.destination_account_id and payment.destination_account_id == payment.journal_id.company_id.transfer_account_id
            payment.is_internal_transfer = is_partner_ok and is_account_ok

    def get_journals_domain(self):
        """
        We get domain here so it can be inherited
        """
        self.ensure_one()
        domain = [('type', 'in', ('bank', 'cash'))]
        if self.payment_type == 'inbound':
            domain.append(('at_least_one_inbound', '=', True))
        # Al final dejamos que para transferencias se pueda elegir
        # cualquier sin importar si tiene outbound o no
        # else:
        elif self.payment_type == 'outbound':
            domain.append(('at_least_one_outbound', '=', True))
        return domain
    #
    @api.depends(
        'payment_type',
    )
    def _compute_journals(self):
        for rec in self:
            rec.journal_ids = rec.journal_ids.search(rec.get_journals_domain())

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_methods(self):
        for rec in self:
            if rec.payment_type in ('outbound') or rec.is_internal_transfer:
                methods = rec.journal_id.outbound_payment_method_ids
            else:
                methods = rec.journal_id.inbound_payment_method_ids
            rec.payment_method_ids = methods

    @api.onchange('currency_id')
    def _onchange_currency(self):
        """ Anulamos metodo nativo que pisa el monto remanente que pasamos
        por contexto TODO ver si podemos re-incorporar esto y hasta extender
        _compute_payment_amount para que el monto se calcule bien aun usando
        el save and new"""
        return False

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """
        Sobre escribimos y desactivamos la parte del dominio de la funcion
        original ya que se pierde si se vuelve a entrar
        """
        # if not self.invoice_ids:
            # Set default partner type for the payment type
        if self.payment_type == 'inbound':
            self.partner_type = 'customer'
        elif self.payment_type == 'outbound':
            self.partner_type = 'supplier'
        else:
            self.partner_type = False
        # limpiamos journal ya que podria no estar disponible para la nueva
        # operacion y ademas para que se limpien los payment methods
        if not self.is_internal_transfer:
            self.journal_id = False
        # # Set payment method domain
        # res = self._onchange_journal()
        # if not res.get('domain', {}):
        #     res['domain'] = {}
        # res['domain']['journal_id'] = self.payment_type == 'inbound' and [
        #     ('at_least_one_inbound', '=', True)] or [
        #     ('at_least_one_outbound', '=', True)]
        # res['domain']['journal_id'].append(('type', 'in', ('bank', 'cash')))
        # return res

    # @api.onchange('partner_type')
    def _onchange_partner_type(self):
        """
        Agregasmos dominio en vista ya que se pierde si se vuelve a entrar
        Anulamos funcion original porque no haria falta
        """
        return False

    def _onchange_amount(self):
        """
        Anulamos este onchange que termina cambiando el domain de journals
        y no es compatible con multicia y se pierde al guardar.
        TODO: ver que odoo con este onchange llama a
        _compute_journal_domain_and_types quien devolveria un journal generico
        cuando el importe sea cero, imagino que para hacer ajustes por
        diferencias de cambio
        """
        return True
    #
    # @api.onchange('journal_id')
    def _onchange_journal(self):
        """
        Sobre escribimos y desactivamos la parte del dominio de la funcion
        original ya que se pierde si se vuelve a entrar
        TODO: ver que odoo con este onchange llama a
        _compute_journal_domain_and_types quien devolveria un journal generico
        cuando el importe sea cero, imagino que para hacer ajustes por
        diferencias de cambio
        """
        if self.journal_id:
            self.currency_id = (self.journal_id.currency_id or self.company_id.currency_id or
                                self.journal_id.company_id.currency_id)
            # Set default payment method
            # (we consider the first to be the default one)
            payment_methods = (
                self.payment_type == 'inbound' and
                self.journal_id.inbound_payment_method_ids or
                self.journal_id.outbound_payment_method_ids)
            # si es una transferencia y no hay payment method de origen,
            # forzamos manual
            if not payment_methods and self.is_internal_transfer:
                payment_methods = self.env.ref(
                    'account.account_payment_method_manual_out')
            self.payment_method_id = (
                payment_methods and payment_methods[0] or False)
            # En version 14 no exite el campo destination_journal_id
            # si se eligió de origen el mismo diario de destino, lo resetiamos
            # if self.journal_id == self.destination_journal_id:
            #     self.destination_journal_id = False
        #     # Set payment method domain
        #     # (restrict to methods enabled for the journal and to selected
        #     # payment type)
        #     payment_type = self.payment_type in (
        #         'outbound', 'transfer') and 'outbound' or 'inbound'
        #     return {
        #         'domain': {
        #             'payment_method_id': [
        #                 ('payment_type', '=', payment_type),
        #                 ('id', 'in', payment_methods.ids)]}}
        # return {}

    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer')
    def _compute_destination_account_id(self):
        """
        We send force_company on context so payments can be created from parent
        companies. We try to send force_company on self but it doesnt works, it
        only works sending it on partner
        """
        res = super(AccountPayment, self)._compute_destination_account_id()
        for rec in self.filtered(
                lambda x: not x.is_internal_transfer):
            partner = self.partner_id.with_company(self.company_id)
            if self.partner_type == 'customer':
                self.destination_account_id = (
                    partner.property_account_receivable_id.id)
            else:
                self.destination_account_id = (
                    partner.property_account_payable_id.id)
        return res

    def _synchronize_to_moves(self, changed_fields):
        #Se modifican las lineas 294 y 296 del metodo original ya que causa conflictos con Grupo de Pago.
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
                'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
                'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id',
        )):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            if liquidity_lines and counterpart_lines and writeoff_lines:

                counterpart_amount = sum(counterpart_lines.mapped('amount_currency'))
                writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))

                # To be consistent with the payment_difference made in account.payment.register,
                # 'writeoff_amount' needs to be signed regarding the 'amount' field before the write.
                # Since the write is already done at this point, we need to base the computation on accounting values.
                if (counterpart_amount > 0.0) == (writeoff_amount > 0.0):
                    sign = -1
                else:
                    sign = 1
                writeoff_amount = abs(writeoff_amount) * sign

                write_off_line_vals = {
                    'name': writeoff_lines[0].name,
                    'amount': writeoff_amount,
                    'account_id': writeoff_lines[0].account_id.id,
                }
            else:
                write_off_line_vals = {}

            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

            line_ids_commands = []
            if liquidity_lines:
                line_ids_commands.append((1, liquidity_lines.id, line_vals_list[0]))
            else:
                line_ids_commands.append((1, 0, line_vals_list[0]))
            if counterpart_lines:
                line_ids_commands.append((1, counterpart_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((1, 0, line_vals_list[1]))

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append((0, 0, extra_line_vals))

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.

            pay.move_id.write({
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            })
