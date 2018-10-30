from .base import BaseOrder, BaseUserOrder
from django.conf import settings
from django.db import models
from decimal import Decimal
from django_fsm import FSMIntegerField, transition
from django.utils.translation import ugettext as _
from core.models import Transaction
from django.core.exceptions import ValidationError


order_books = {}


class BaseLimitOrder(BaseOrder):

    class Meta:
        abstract = True

    rate = models.DecimalField(max_digits=18, decimal_places=8, blank=True,
                               null=True)
    order_book = models.ForeignKey(
        'orders.OrderBook', on_delete=models.DO_NOTHING, null=True
    )

    def save(self, *args, **kwargs):
        if not self.unique_reference:
            self.unique_reference = \
                self.gen_unique_value(
                    lambda x: self.get_random_unique_reference(x),
                    lambda x: self.__class__.objects.filter(
                        unique_reference=x).count(),
                    settings.UNIQUE_REFERENCE_LENGTH
                )
        self.rate = self._rate
        super(BaseLimitOrder, self).save(*args, **kwargs)


class Trade(BaseLimitOrder):
    sell_order = models.ForeignKey(
        'orders.LimitOrder',
        on_delete=models.DO_NOTHING,
        related_name='sell_trades',
        default=None, blank=True, null=True
    )
    buy_order = models.ForeignKey(
        'orders.LimitOrder',
        on_delete=models.DO_NOTHING,
        related_name='buy_trades',
        default=None, blank=True, null=True
    )

    def save(self, *args, **kwargs):
        super(Trade, self).save(*args, **kwargs)
        if self.sell_order:
            self.sell_order.save(
                update_fields=['rate', 'closed_amount_base',
                               'closed_amount_quote']
            )
        if self.buy_order:
            self.buy_order.save(
                update_fields=['rate', 'closed_amount_base',
                               'closed_amount_quote']
            )

    def __str__(self):
        name = \
            '{pair} {amount_base}({base})@{rate}={amount_quote}({quote}) / ' \
            '{unique_reference}'.format(
                pair=self.pair.name,
                amount_base=str(self.amount_base).rstrip('0').rstrip('.'),
                amount_quote=str(self.amount_quote).rstrip('0').rstrip('.'),
                rate=str(self.rate).rstrip('0').rstrip('.'),
                base=self.pair.base.code,
                quote=self.pair.quote.code,
                unique_reference=self.unique_reference
            )
        return name


class LimitOrder(BaseLimitOrder, BaseUserOrder):

    INITIAL = BaseUserOrder.INITIAL
    PAID_UNCONFIRMED = BaseUserOrder.PAID_UNCONFIRMED
    PAID = BaseUserOrder.PAID
    PRE_RELEASE = BaseUserOrder.PRE_RELEASE
    RELEASED = BaseUserOrder.RELEASED
    COMPLETED = BaseUserOrder.COMPLETED
    CANCELED = BaseUserOrder.CANCELED
    REFUNDED = BaseUserOrder.REFUNDED
    STATUS_TYPES = BaseUserOrder.STATUS_TYPES
    _order_status_help = BaseUserOrder._order_status_help

    NEW = 0
    OPEN = 5
    CLOSED = 10
    BOOK_STATUS_TYPES = (
        (NEW, _('NEW')),
        (OPEN, _('OPEN')),
        (CLOSED, _('CLOSED')),
    )
    _could_be_paid_msg = 'Could be paid by crypto transaction or fiat ' \
                         'payment, depending on order_type.'
    _book_status_help_list = (
        'NEW', 'Order is created, not on the book.',
        'OPEN', 'Order is on the book.',
        'CLOSED', 'Order is closed, not on the book anymore.',
    )
    _book_status_help = \
        ((len(_book_status_help_list) // 2) * '{} - {}<br/>').format(
            *_book_status_help_list
        )

    limit_rate = models.DecimalField(max_digits=18, decimal_places=8,
                                     blank=True, null=True)
    closed_amount_base = models.DecimalField(
        max_digits=18, decimal_places=8, blank=True, null=True,
        default=Decimal('0')
    )
    closed_amount_quote = models.DecimalField(
        max_digits=18, decimal_places=8, blank=True, null=True,
        default=Decimal('0')
    )
    status = FSMIntegerField(choices=STATUS_TYPES, default=INITIAL,
                             help_text=_order_status_help, db_index=True)
    book_status = FSMIntegerField(choices=BOOK_STATUS_TYPES, default=NEW,
                                  help_text=_book_status_help, db_index=True)

    @property
    def book_status_name(self):
        return [s for s in self.BOOK_STATUS_TYPES if s[0] == self.book_status]

    @property
    def remaining_amount_base(self):
        return self.amount_base - self.closed_amount_base

    @property
    def remaining_amount_quote(self):
        return self.amount_quote - self.closed_amount_quote

    @property
    def _rate(self):
        if self.closed_amount_quote and self.closed_amount_base:
            return self.closed_amount_quote / self.closed_amount_base

    @property
    def token(self):
        return

    def _validate_status(self, status):
        if not self.pk:
            return
        old_order = LimitOrder.objects.get(pk=self.pk)
        old_status = old_order.status
        if old_status > status:
            raise ValidationError(
                _('Cannot set limit_order status from {} to {}'.format(
                    old_status, status
                )))

    def _validate_book_status(self, status):
        if not self.pk:
            return
        old_order = LimitOrder.objects.get(pk=self.pk)
        old_status = old_order.book_status
        if old_status > status:
            raise ValidationError(
                _('Cannot set limit_order book_status from {} to {}'.format(
                    old_status, status
                )))

    def _validate_fields(self):
        self._validate_status(self.status)
        self._validate_book_status(self.book_status)

    def save(self, *args, **kwargs):
        self._validate_fields()
        if not self.pk:
            self.calculate_limit_amounts()
        if self.sell_trades.count() or self.buy_trades.count():
            self.calculate_closed_amounts()
        self.exchange = self.pair.is_crypto
        super(LimitOrder, self).save(*args, **kwargs)

    def calculate_closed_amounts(self):
        trades = Trade.objects.filter(
            models.Q(sell_order=self) | models.Q(buy_order=self)
        ).aggregate(models.Sum('amount_base'), models.Sum('amount_quote'))
        self.closed_amount_base = trades.get('amount_base__sum')
        self.closed_amount_quote = trades.get('amount_quote__sum')

    def calculate_limit_amounts(self):
        if self.amount_quote and not self.amount_base and self.limit_rate:
            self.amount_base = self.amount_quote / self.limit_rate
        elif self.amount_quote and self.amount_base and not self.limit_rate:
            self.limit_rate = self.amount_quote / self.amount_base
        else:
            self.amount_quote = self.amount_base * self.limit_rate

    def calculate_order(self, deposit_amount):
        if self.deposit_amount != deposit_amount:
            if self.deposit_currency == self.pair.quote:
                self.amount_quote = deposit_amount
                self.amount_base = self.amount_quote / self.limit_rate
            elif self.deposit_currency == self.pair.base:
                self.amount_base = deposit_amount
                self.amount_quote = self.amount_base * self.limit_rate
            self.save(update_fields=['amount_base', 'amount_quote'])

    def get_or_create_order_book(self, pair):
        res = order_books.get(pair)
        if not res or res != self.order_book.book_obj:
            # make sure that book is not only on memory
            res = order_books[pair] = self.order_book.book_obj
        return res

    def _create_trade(self, trades):
        res = []
        for _trade in trades:
            party1 = _trade['party1']
            party2 = _trade['party2']
            amount_base = _trade['quantity']
            amount_quote = _trade['price'] * amount_base
            sell_ref = [x[0] for x in [party1, party2] if x[1] == 'ask'][0]
            buy_ref = [x[0] for x in [party1, party2] if x[1] == 'bid'][0]
            sell_order = LimitOrder.objects.get(unique_reference=sell_ref)
            buy_order = LimitOrder.objects.get(unique_reference=buy_ref)
            assert sell_order.pair == buy_order.pair
            assert sell_order.order_type == self.SELL
            assert buy_order.order_type == self.BUY
            trade, created = Trade.objects.get_or_create(
                sell_order=sell_order,
                buy_order=buy_order,
                amount_quote=amount_quote,
                amount_base=amount_base,
                pair=sell_order.pair
            )
            res.append(trade)
        return res

    @property
    def filled(self):
        if self.order_type == self.BUY and self.buy_trades.count():
            # BUY order filling is counted on amount_quote because that
            # is what user deposited
            trades_amount = self.buy_trades.all().aggregate(
                models.Sum('amount_quote')
            ).get('amount_quote__sum')
            trades_amount = trades_amount if trades_amount else Decimal('0')
            return trades_amount / self.amount_quote
        if self.order_type == self.SELL and self.sell_trades.count():
            # SELL order filling is counted on amount_base because that
            # is what user deposited
            trades_amount = self.sell_trades.all().aggregate(
                models.Sum('amount_base')
            ).get('amount_base__sum')
            trades_amount = trades_amount if trades_amount else Decimal('0')
            return trades_amount / self.amount_base

        return Decimal('0')

    def __str__(self):
        name = \
            '{pair} {type} {amount_base}({base})@{limit_rate} / ' \
            '{unique_reference} {username} {book_status} {status}'.format(
                username=self.user.username,
                type=self.get_order_type_display(),
                status=self.get_status_display(),
                book_status=self.get_book_status_display(),
                pair=self.pair.name,
                amount_base=str(self.amount_base).rstrip('0').rstrip('.'),
                amount_quote=str(self.amount_quote).rstrip('0').rstrip('.'),
                limit_rate=str(self.limit_rate).rstrip('0').rstrip('.'),
                base=self.pair.base.code,
                quote=self.pair.quote.code,
                unique_reference=self.unique_reference
            )
        return name

    @transition(field=status, source=INITIAL, target=PAID_UNCONFIRMED)
    def _register_deposit(self, tx_data, crypto=True):
        model = Transaction
        amount_key = 'amount'
        order = tx_data.get('limit_order')
        assert tx_data.get('order') is None
        tx_type = tx_data.get('type')
        tx_amount = tx_data.get(amount_key)
        tx_currency = tx_data.get('currency')
        if order.deposit_currency == 'XRP':
            tx_destination_tag = tx_data.get('destination_tag')
            if order.destination_tag != tx_destination_tag:
                raise ValidationError(
                    'Bad tx destination tag {}. Should be {}'.format(
                        order, self
                    )
                )
        if order.deposit_currency == 'XMR':
            tx_payment_id = tx_data.get('payment_id')
            if order.payment_id != tx_payment_id:
                raise ValidationError(
                    'Bad tx payment id {}. Should be {}'.format(
                        order, self
                    )
                )

        if order != self:
            raise ValidationError(
                'Bad order {} on the deposit tx. Should be {}'.format(
                    order, self
                )
            )
        if self.deposit_currency != tx_currency:
            raise ValidationError(
                'Bad tx currency {}. Order quote currency {}'.format(
                    tx_currency, self.deposit_currency
                )
            )
        if tx_type != Transaction.DEPOSIT:
            raise ValidationError(
                'Order {}. Cannot register DEPOSIT - wrong transaction '
                'type {}'.format(self, tx_type))

        if not tx_amount:
            raise ValidationError(
                'Order {}. Cannot register DEPOSIT - bad amount - {}'.format(
                    self, tx_amount))

        # Transaction is created before calculate_order to assure that
        # it will not be hanging (waiting for better rate).

        tx = model(**tx_data)
        tx.save()
        self.calculate_order(tx_amount)

        return tx

    def register_deposit(self, tx_data, crypto=True):
        res = {'status': 'OK'}
        try:
            tx = self._register_deposit(tx_data, crypto=crypto)
            res.update({'tx': tx})
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
            self.refresh_from_db()
        self.save()
        return res

    @transition(field=status, source=PAID_UNCONFIRMED, target=PAID)
    def _confirm_deposit(self, tx, **kwargs):
        assert self.book_status == self.CLOSED
        assert self.filled == Decimal('1')
        success_params = ['is_completed', 'is_verified']
        if tx.type != Transaction.DEPOSIT:
            raise ValidationError(
                'Order {}. Cannot confirm DEPOSIT - wrong transaction '
                'type {}'.format(self, tx.type))
        for param in success_params:
            if getattr(tx, param):
                raise ValidationError(
                    'Order {}.Cannot confirm DEPOSIT - already confirmed({}).'
                    ''.format(self, param)
                )
            setattr(tx, param, True)
        tx.save()

    def confirm_deposit(self, tx, **kwargs):
        res = {'status': 'OK'}
        try:
            self._confirm_deposit(tx, **kwargs)
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
        self.save()
        return res

    @transition(field=status, source=PAID, target=PRE_RELEASE)
    def _pre_release(self, api=None):
        healthy = api.health_check(self.withdraw_currency)
        if not healthy:
            raise ValidationError(_(
                'Wallet {} isin\'t working before the release'.format(
                    self.pair.base.wallet
                )
            ))
        return healthy

    def pre_release(self, api=None):
        res = {'status': 'OK'}
        try:
            self._pre_release(api=api)
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
        self.save()
        return res

    @transition(field=status, source=PRE_RELEASE, target=RELEASED)
    def _release(self, tx_data, api=None, currency=None, amount=None):
        if currency != self.withdraw_currency \
                or amount != self.withdraw_amount:
            raise ValidationError(
                'Wrong amount {} or currency {} for order {} release'.format(
                    amount, currency, self.unique_reference
                )
            )
        old_withdraw_txs = self.transactions.exclude(
            type__in=[Transaction.DEPOSIT, Transaction.INTERNAL]
        )
        tx_type = tx_data.get('type')
        if tx_type != Transaction.WITHDRAW:
            msg = 'Bad Transaction type'
            raise ValidationError(msg)
        if len(old_withdraw_txs) == 0:
            tx = Transaction(**tx_data)
            tx.save()

            payment_id = self.payment_id \
                if self.payment_id is not None \
                else None
            destination_tag = self.destination_tag if \
                self.destination_tag is not None \
                else None
            tx_id, success = api.release_coins(
                currency, self.withdraw_address, amount,
                payment_id=payment_id, destination_tag=destination_tag
            )
            setattr(tx, api.TX_ID_FIELD_NAME, tx_id)
            tx.save()
        else:
            msg = 'Order {} already has WITHDRAW or None type ' \
                  'transactions {}'.format(self, old_withdraw_txs)
            self.flag(val=msg)
            raise ValidationError(msg)

        if not tx_id:
            msg = 'Payment release returned None, order {}'.format(self)
            self.flag(val=msg)
            raise ValidationError(msg)

        if success:
            tx.is_verified = True
            tx.save()
        return tx

    @transition(field=status, source=RELEASED, target=COMPLETED)
    def _complete(self, tx):
        if tx.type != Transaction.WITHDRAW:
            raise ValidationError(
                'Order {}. Cannot confirm WITHDRAW - wrong transaction '
                'type'.format(self))
        if tx.is_completed:
            raise ValidationError(
                'Order {}.Cannot confirm DEPOSIT - already confirmed.'.format(
                    self))
        tx.is_completed = True
        tx.is_verified = True
        tx.save()

    def complete(self, tx):
        res = {'status': 'OK'}
        try:
            self._complete(tx)
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
        self.save()
        return res

    def release(self, tx_data, api=None):
        res = {'status': 'OK'}
        try:
            currency = tx_data.get('currency')
            amount = tx_data.get('amount')
            tx = self._release(tx_data, api=api, currency=currency,
                               amount=amount)
            res.update({'tx': tx})
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
        self.save()
        return res

    @transition(field=book_status, source=NEW, target=OPEN)
    def _open(self, tx):
        assert tx.currency == self.deposit_currency
        assert tx.confirmations >= self.deposit_currency.min_order_book_confirmations  # noqa
        assert self.status == self.PAID_UNCONFIRMED
        assert self.sell_trades.count() == 0 and self.buy_trades.count() == 0
        order_book = self.get_or_create_order_book(self.pair)
        if not self.pk:
            return {}
        _payload = {
            'type': 'limit',
            'side': 'bid' if self.order_type == self.BUY else 'ask',
            'quantity': self.amount_base,
            'price': self.limit_rate,
            'trade_id': self.unique_reference
        }
        res = order_book.process_order(_payload, False, False)
        trades = self._create_trade(order_book.tape)
        return {'res': res, 'order_book': order_book, 'trades': trades}

    def open(self, tx):
        res = {'status': 'OK'}
        trades = None
        try:
            o_resp = self._open(tx)
            res.update(o_resp)
            trades = o_resp.get('trades')
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
            self.refresh_from_db()
        self.save()
        if trades:
            for trade in trades:
                so = trade.sell_order
                bo = trade.buy_order
                if so and so.filled == Decimal('1'):
                    so.refresh_from_db()
                    so.close()
                if bo and bo.filled == Decimal('1'):
                    bo.refresh_from_db()
                    bo.close()
        if res['status'] == 'OK':
            # move it to task when need to increase speed
            order_book = self.get_or_create_order_book(self.pair)
            self.order_book.book_obj = order_book
            self.order_book.save()
        return res

    @transition(field=book_status, source=OPEN, target=CLOSED)
    def _close(self):
        assert self.filled == Decimal('1')

    def close(self):
        res = {'status': 'OK'}
        try:
            self._close()
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
            self.refresh_from_db()
        self.save()
        return res
