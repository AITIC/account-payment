##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cashbox_session_id = fields.Many2one(
        'account.cashbox.session',
        string='POP Session',
        # compute="_compute_cashbox_session_id", --- Se reemplaza el compute por un default
        default=lambda self: self._default_cashbox_session_id(),
        readonly=True,
        store=True
    )
    requiere_account_cashbox_session = fields.Boolean(
        compute='_compute_requiere_account_cashbox_session',
        compute_sudo=False,
    )

    cashbox_payment_method_ids = fields.Many2many('account.journal', compute="_compute_cashbox_payment_method_ids", string="Payment Methods", readonly=True, store=True)
    cashbox_filter = fields.Binary(string='Cashbox Filter', compute="_compute_cashbox_payment_method_ids", readonly=True)
    destination_journal_filter = fields.Binary(string='Destination Journal Filter', compute="_compute_destination_journal_filter", readonly=True)


    @api.depends('cashbox_session_id')
    def _compute_cashbox_payment_method_ids(self):
        for rec in self:
            rec.cashbox_payment_method_ids = rec.cashbox_session_id.cashbox_id.journal_ids
            if rec.cashbox_payment_method_ids:
                rec.cashbox_filter = [('id','in',rec.cashbox_payment_method_ids.ids),('default_account_payment_group','=',False)] 
            else:
                rec.cashbox_filter = [('type','in',['cash','bank']),('company_id','=',rec.company_id.id),('default_account_payment_group','=',False)]

    @api.depends('cashbox_session_id', 'journal_id', 'company_id', 'available_journal_ids')
    def _compute_destination_journal_filter(self):
        for rec in self:
            base_domain = [
                ('company_id', 'in', [False, rec.company_id.id]),
                '|',
                ('company_id', '=', False),
                ('company_id', 'parent_of', rec.company_id.id),
                ('type', 'in', ('bank', 'cash')),
                ('id', '!=', rec.journal_id.id)
            ]
            if rec.cashbox_session_id:
                base_domain += [('id', 'in', rec.available_journal_ids.ids)]

            rec.destination_journal_filter = base_domain
            
    @api.depends_context('uid')
    # dummy depends para que se compute(no estamos seguros porque solo con el depends_context no computa)
    @api.depends('partner_id')
    def _compute_requiere_account_cashbox_session(self):
        self.requiere_account_cashbox_session = self.env.user.requiere_account_cashbox_session

    # INICIO - Se reemplaza el compute por un default
    def _default_cashbox_session_id(self):

        # si estamos en un cheque, tomamos la sesion de la ultima operacion
        if self.env.context and 'active_model' in self.env.context and self.env.context['active_model'] == 'account.check':
            check_id = self.env['account.check'].browse(self.env.context['active_id'])
            last_operation = check_id.operation_ids.sorted(key=lambda r: r.id, reverse=True)[:1]
            if last_operation:
                if last_operation[0].origin and last_operation[0].origin.cashbox_session_id:
                    return last_operation[0].origin.cashbox_session_id.id
                else:
                    return False
                
        session_ids = self.env['account.cashbox.session'].search([
            ('state', '=', 'opened'),
            '|',
            ('user_ids', '=', self.env.uid),
            ('user_ids', '=', False),
        ])
        return session_ids.id if len(session_ids) == 1 else False
    
    # def _compute_cashbox_session_id(self):
    #     for rec in self:
    #         session_ids = self.env['account.cashbox.session'].search([
    #             ('state', '=', 'opened'),
    #             '|',
    #             ('user_ids', '=', self.env.uid),
    #             ('user_ids', '=', False),
    #         ])
    #         if len(session_ids) == 1:
    #             rec.cashbox_session_id = session_ids.id
    #         else:
    #             rec.cashbox_session_id = False

    # FIN - Se reemplaza el compute por un default

    @api.constrains('journal_id', 'currency_id', 'cashbox_session_id')
    def check_journal_currency(self):
        for payment in self.filtered('cashbox_session_id'):
            if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
                raise ValidationError(
                    _('The currency of the journal must be the of the payment.'))

    def _create_paired_internal_transfer_payment(self):
        super(AccountPayment, self.with_context(paired_transfer=True))._create_paired_internal_transfer_payment()

    def action_post(self):
        for rec in self:
            if rec.cashbox_session_id and rec.cashbox_session_id.state != 'opened':
                raise UserError(_(
                    "A payment (id %s) can't be posted on a pos session that is not open (session %s)'" % (
                        rec.id, rec.cashbox_session_id.name
                    )))

            if  not self.env.context.get('paired_transfer') and self.env.user.requiere_account_cashbox_session and not rec.cashbox_session_id:
                raise UserError(_('Your user requires to use payment session on each payment'))

        res = super().action_post()
        for rec in self:
            if rec.cashbox_session_id:
                for line in rec.account_payment_group_ids:
                    line.write({'cashbox_session_id': rec.cashbox_session_id.id})
            # si es una transferencia interna y esta en una sesion abierta, creamos un account.payment.group
            if rec.state == 'posted' and rec.is_internal_transfer and rec.cashbox_session_id and rec.cashbox_session_id.state == 'opened':
                dict_apg = {
                    'move_id': rec.move_id.id,
                    'account_payment_id': rec.id,
                    'currency_id': rec.currency_id.id,
                    'partner_id': rec.partner_id.id,
                    'date': rec.date,
                    'journal_id': rec.destination_journal_id.id,
                    'amount': rec.amount,
                    'payment_method_line_id': rec.payment_method_line_id.id,
                }
                account_payment_group = self.env['account.payment.group'].create(dict_apg)
                rec.account_payment_group_id = account_payment_group.id
        return res

    def action_cancel(self):
        closed_sessions = self.filtered(lambda x: x.cashbox_session_id.state == 'closed')
        if closed_sessions:
            raise UserError(_(
                "Can't cancel a payment on a closed payment session. Payment ids: %s") % closed_sessions.ids)
        super().action_cancel()

    @api.depends('payment_type', 'cashbox_session_id')
    def _compute_available_journal_ids(self):
        super()._compute_available_journal_ids()
        for pay in self.filtered('cashbox_session_id'):
            # hacemos dominio sobre los line_ids y no los diarios del pop config porque
            # puede ser que sea una sesion vieja y que el setting pop config cambie
            pay_group_journal = self.env['account.journal'].get_default_payment_group_journal()
            pay.available_journal_ids = pay.available_journal_ids._origin.filtered(
                lambda x: x in pay.cashbox_session_id.line_ids.mapped('journal_id') | pay_group_journal)

    @api.onchange('cashbox_session_id')
    def _onchange_cashbox_session(self):
        """ Esto es para refrescar el primer journal seleccionado por si no esta en la lista de los permitidos.
        Me suena que en algun otro lugar lo hicimos de otra manera"""
        for rec in self:
            if rec.journal_id not in rec.available_journal_ids._origin:
                rec.journal_id = rec.available_journal_ids._origin[:1]

