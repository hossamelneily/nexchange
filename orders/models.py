from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext as _

from core.common.models import (SoftDeletableModel, TimeStampedModel,
                                UniqueFieldMixin, FlagableMixin)
from core.models import Pair, Transaction, Currency
from payments.utils import money_format
from payments.models import Payment
from ticker.models import Price
from django.core.exceptions import ValidationError
from django.db.models import Q
from math import log10, floor, ceil
from django.utils.translation import activate
from nexchange.utils import send_email, send_sms, get_nexchange_logger
from django_fsm import FSMIntegerField, transition
from nexchange.celery import app
from cached_property import cached_property_with_ttl
from payments.api_clients.safe_charge import SafeChargeAPIClient
from payments.models import PaymentPreference
from nexchange.api_clients.factory import ApiClientFactory
from oauth2_provider.models import AccessToken
from decimal import InvalidOperation
from core.validators import validate_xmr_payment_id, validate_destination_tag

safe_charge_client = SafeChargeAPIClient()
factory = ApiClientFactory()
logger = get_nexchange_logger('Order logger', with_email=True,
                              with_console=True)


class Order(TimeStampedModel, SoftDeletableModel,
            UniqueFieldMixin, FlagableMixin):

    RETRY_RELEASE = 'orders.task_summary.release_retry_invoke'

    BUY = 1
    SELL = 0
    TYPES = (
        (SELL, 'SELL'),
        (BUY, 'BUY'),
    )
    _order_type_help = (3 * '{} - {}<br/>').format(
        _('BUY'), _('Customer is giving fiat, and getting crypto money.'),
        _('SELL'), _('Customer is giving crypto and getting fiat money'),
        _('EXCHANGE'), _('Customer is exchanging different kinds of crypto '
                         'currencies')
    )

    CANCELED = 0
    INITIAL = 11
    PAID_UNCONFIRMED = 12
    PAID = 13
    PRE_RELEASE = 14
    RELEASED = 15
    COMPLETED = 16
    REFUNDED = 8
    STATUS_TYPES = (
        (PAID_UNCONFIRMED, _('UNCONFIRMED PAYMENT')),
        (PRE_RELEASE, _('PRE-RELEASE')),
        (CANCELED, _('CANCELED')),
        (INITIAL, _('INITIAL')),
        (PAID, _('PAID')),
        (RELEASED, _('RELEASED')),
        (COMPLETED, _('COMPLETED')),
        (REFUNDED, _('REFUNDED')),
    )
    IN_PAID = [PAID, RELEASED, COMPLETED, PRE_RELEASE]
    IN_RELEASED = [RELEASED, COMPLETED, PRE_RELEASE]
    IN_SUCCESS_RELEASED = [RELEASED, COMPLETED]
    IN_COMPLETED = [COMPLETED]
    REFUNDABLE_STATES = [PAID_UNCONFIRMED, PAID, PRE_RELEASE]
    _could_be_paid_msg = 'Could be paid by crypto transaction or fiat ' \
                         'payment, depending on order_type.'
    _order_status_help = (6 * '{} - {}<br/>').format(
        'INITIAL', 'Initial status of the order.',
        'PAID', 'Order is Paid by customer. ' + _could_be_paid_msg,
        'PAID_UNCONFIRMED', 'Order is possibly paid (unconfirmed crypto '
                            'transaction or fiat payment is to small to '
                            'cover the order.)',
        'PRE_RELEASE', 'Order is prepared for RELEASE.',
        'RELEASED', 'Order is paid by service provider. ' + _could_be_paid_msg,
        'COMPLETED', 'All statuses of the order is completed',
        'CANCELED', 'Order is canceled.',
        'REFUNDED', 'Order is refunded',
    )

    PROVIDED_BASE = 0
    PROVIDED_QUOTE = 1
    PROVIDED_BOTH = 2
    PROVIDED_AMOUNT_OPTIONS = (
        (PROVIDED_BASE, _('amount_base')),
        (PROVIDED_QUOTE, _('amount_quote')),
        (PROVIDED_BOTH, _('amount_quote and amount_base')),
    )

    # Todo: inherit from BTC base?, move lengths to settings?
    order_type = models.IntegerField(
        choices=TYPES, default=BUY, help_text=_order_type_help
    )
    exchange = models.BooleanField(default=False)
    status = FSMIntegerField(choices=STATUS_TYPES, default=INITIAL,
                             help_text=_order_status_help)
    amount_base = models.DecimalField(max_digits=18, decimal_places=8,
                                      blank=True)
    amount_quote = models.DecimalField(max_digits=18, decimal_places=8,
                                       blank=True)
    payment_window = models.IntegerField(default=settings.PAYMENT_WINDOW)
    unpaid_order_window = models.IntegerField(
        default=settings.UNPAID_CANCEL_WINDOW_MINUTES
    )
    user = models.ForeignKey(User, related_name='orders')
    unique_reference = models.CharField(
        max_length=settings.UNIQUE_REFERENCE_MAX_LENGTH)
    admin_comment = models.CharField(max_length=200)
    payment_preference = models.ForeignKey('payments.PaymentPreference',
                                           default=None,
                                           null=True, blank=True)
    withdraw_address = models.ForeignKey('core.Address',
                                         null=True,
                                         blank=True,
                                         related_name='order_set_withdraw',
                                         default=None)
    deposit_address = models.ForeignKey('core.Address',
                                        null=True,
                                        blank=True,
                                        related_name='order_set_deposit',
                                        default=None)
    refund_address = models.ForeignKey(
        'core.Address', null=True, blank=True, related_name='order_set_refund',
        default=None
    )
    payment_id = models.CharField(
        max_length=64, null=True, blank=True, default=None,
        validators=[validate_xmr_payment_id]
    )
    destination_tag = models.CharField(
        max_length=10, null=True, blank=True, default=None,
        validators=[validate_destination_tag]
    )
    is_default_rule = models.BooleanField(default=False)
    from_default_rule = models.BooleanField(default=False)
    pair = models.ForeignKey(Pair)
    price = models.ForeignKey(Price, null=True, blank=True)
    user_marked_as_paid = models.BooleanField(default=False)
    system_marked_as_paid = models.BooleanField(default=False)
    user_provided_amount = models.IntegerField(
        choices=PROVIDED_AMOUNT_OPTIONS, default=PROVIDED_BASE)
    slippage = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal('0'),
    )
    set_as_paid_on = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        ordering = ['-created_on']
        # unique_together = ['deleted', 'unique_reference']

    def validate_unique(self, exclude=None):
        # TODO: exclude expired?
        if not self.deleted and \
                Order.objects.exclude(pk=self.pk).filter(
                    unique_reference=self.unique_reference,
                    deleted=False).exists():
            raise ValidationError(
                'Un-deleted order with same reference exists')

        super(Order, self).validate_unique(exclude=exclude)

    def _types_range_constraint(self, field, types):
        """ This is used for validating IntegerField's with choices.
        Assures that value is in range of choices.
        """
        if field > max([i[0] for i in types]):
            raise ValidationError(_('Invalid order type choice'))
        elif field < min([i[0] for i in types]):
            raise ValidationError(_('Invalid order type choice'))

    def get_amount_base_min(self, user_format=False):
        _base_min = self.pair.base.minimal_amount
        if not user_format:
            return _base_min
        _quote_min = self.get_amount_quote_min(user_format=False)
        if _quote_min is None:
            return _base_min
        _min_list = [_base_min]
        _order = Order(pair=self.pair, amount_quote=_quote_min,
                       price=self.price)
        _order.calculate_base_from_quote()
        diff = settings.SATOSHI if self.pair.quote.is_crypto else Decimal('0')
        _min_list.append(_order.amount_base + diff)
        return max(_min_list)

    def get_amount_base_max(self, user_format=False):
        if self.pk:
            return
        _base_max = None if self.pair.base.execute_cover \
            else self.pair.base.available_main_reserves
        if not user_format:
            return _base_max
        _quote_max = self.get_amount_quote_max(user_format=False)
        if _quote_max is None:
            return _base_max
        _max_list = [_base_max] if _base_max else []
        _order = Order(pair=self.pair, amount_quote=_quote_max,
                       price=self.price)
        _order.calculate_base_from_quote()
        diff = settings.SATOSHI if self.pair.base.is_crypto else Decimal('0')
        _max_list.append(_order.amount_base - diff)
        return min(_max_list)

    def get_amount_quote_max(self, user_format=False):
        if self.pk:
            return
        _quote_max = self.pair.quote.maximal_amount
        if not user_format:
            return _quote_max
        _base_max = self.get_amount_base_max(user_format=False)
        if not _base_max:
            return _quote_max
        _max_list = [_quote_max]
        _order = Order(pair=self.pair, amount_base=_base_max,
                       price=self.price)
        _order.calculate_quote_from_base()
        diff = settings.SATOSHI if self.pair.quote.is_crypto else Decimal('0')
        _max_list.append(_order.amount_quote - diff)
        return min(_max_list)

    def get_amount_quote_min(self, user_format=False):
        if self.pk:
            return
        _quote_min = \
            None if self.pair.is_crypto else self.pair.quote.minimal_amount
        if not user_format:
            return _quote_min
        _base_min = self.get_amount_base_min(user_format=False)
        if not _base_min:
            return _quote_min
        _min_list = [_quote_min] if _quote_min else []
        _order = Order(pair=self.pair, amount_base=_base_min,
                       price=self.price)
        _order.calculate_quote_from_base()
        diff = settings.SATOSHI if self.pair.quote.is_crypto else Decimal('0')
        _min_list.append(_order.amount_quote + diff)
        return max(_min_list)

    def _validate_order_amount(self):
        _raise_error = False
        # _error_type is either 'min' or 'max'
        _error_type = None
        _error_amount_type = \
            'amount_base' if self.user_provided_amount == self.PROVIDED_BASE \
            else 'amount_quote'
        # _direction is either 'receive' or 'deposit' (terms form UI)
        _direction = \
            'receive' if self.user_provided_amount == self.PROVIDED_BASE \
            else 'deposit'
        _currency_code = \
            self.pair.base.code \
            if self.user_provided_amount == self.PROVIDED_BASE \
            else self.pair.quote.code
        # actual restricted amount (might be converted)
        _final_amount = None
        # Message template - end user must understand this
        _error_template = \
            '{_error_type}imum {_direction} amount is {_final_amount} ' \
            '{_currency_code} on this trade.'

        for _amount_type in ['amount_quote', 'amount_base']:
            _min = getattr(self, 'get_{}_min'.format(_amount_type))()
            _max = getattr(self, 'get_{}_max'.format(_amount_type))()
            _amount = getattr(self, _amount_type)
            if _min is not None and _amount < _min:
                _raise_error = True
                _error_type = 'min'
                break
            if _max is not None and _amount > _max:
                _raise_error = True
                _error_type = 'max'
                break

        if _raise_error:
            _final_amount = getattr(
                self, 'get_{}_{}'.format(_error_amount_type, _error_type)
            )(user_format=True)
            if _final_amount is None:
                _error_msg = \
                    'Cannot initiate this trade, please contact support.'
            else:
                _error_msg = _error_template.format(
                    _error_type=_error_type.capitalize(),
                    _direction=_direction,
                    _currency_code=_currency_code,
                    _final_amount=str(_final_amount).rstrip('0').rstrip('.'),
                )
            raise ValidationError(_error_msg)

    def _validate_status(self, status):
        if not self.pk:
            return
        old_order = Order.objects.get(pk=self.pk)
        old_status = old_order.status
        if old_status == status:
            return
        elif old_status == Order.CANCELED and status != Order.CANCELED:
            raise ValidationError(
                _('Cannot set order status to {} when it is CANCELED'.format(
                    status)))
        elif status == Order.CANCELED:
            if old_status in [Order.INITIAL, Order.CANCELED,
                              Order.PAID_UNCONFIRMED]:
                return
            else:
                raise ValidationError(
                    _('Cannot CANCEL order which is status is {}'.format(
                        old_order.get_status_display()
                    ))
                )
        elif status == Order.REFUNDED:
            if old_status in self.REFUNDABLE_STATES:
                return
            else:
                raise ValidationError(
                    _('Cannot REFUND order which is status is {}'.format(
                        old_order.get_status_display()
                    ))
                )
        elif status < old_status:
            raise ValidationError(
                _('Cannot set order status from {} to {}'
                  '(must be incremential)'.format(old_status, status)))
        else:
            return

    def _validate_pair(self):
        if not self.pk:
            self.pair.refresh_from_db()
            self.pair.validate_enabled()
            self.pair.validate_user(self.user)

    def _validate_price(self):
        if not self.pk and self.price.expired:
            error_msg = 'Pair {} is temporarily unavailable.'.format(
                self.pair.name
            )
            logger.warning('{}. Ticker expired !!!'.format(error_msg))
            raise ValidationError(
                _(error_msg.format(self.pair.name))
            )

    def _validate_reserves(self):
        error_msg = 'Pair {} is temporarily unavailable.'.format(
            self.pair.name
        )
        if not self.pk:
            if self.pair.base.is_crypto:
                base_reserves = self.pair.base.available_reserves
                min_base_reserves = self.pair.base.reserve.minimum_level
                if base_reserves < min_base_reserves:
                    logger.warning(
                        '{}. Base Reserves too low.'.format(error_msg)
                    )
                    raise ValidationError(_(error_msg))
            if self.pair.quote.is_crypto:
                quote_reserves = self.pair.quote.available_reserves
                min_quote_reserves = self.pair.quote.reserve.maximum_level
                if quote_reserves > min_quote_reserves:
                    logger.warning('{}. Quote Reserves too high.'.format(
                        error_msg
                    ))
                    logger.warning(error_msg)
                    raise ValidationError(_(error_msg))

    def _validate_address(self):
        if not self.pk and getattr(self.withdraw_address, 'blocked', False):
            raise ValidationError(_('Address {} is blocked.'.format(
                self.withdraw_address.address
            )))

    def _validate_fields(self):
        self._types_range_constraint(self.order_type, self.TYPES)
        self._types_range_constraint(self.status, self.STATUS_TYPES)
        self._validate_status(self.status)
        self._validate_pair()
        self._validate_address()
        if all([not self.amount_base, not self.amount_quote]):
            raise ValidationError(
                _('One of amount_quote and amount_base is required.'))
        if all([self.pair.base != Currency.objects.get(code='XMR'),
                self.payment_id is not None]):
            raise ValidationError(
                _('Payment id is currently used only for Monero address'))
        if all([not self.pair.includes_currency('XRP'),
                self.destination_tag is not None]):
            raise ValidationError(
                _('Destination tag is currently used only for Ripple address'))

    def clean(self, *args, **kwargs):
        self._validate_fields()
        super(Order, self).clean(*args, **kwargs)

    def set_provided_amount_option(self):
        if not self.pk:
            self.user_provided_amount = self.get_provided_amount_option()

    def get_provided_amount_option(self):
        if all([self.amount_quote, self.amount_base]):
            return self.PROVIDED_BOTH
        elif self.amount_base:
            return self.PROVIDED_BASE
        elif self.amount_quote:
            return self.PROVIDED_QUOTE

    def set_payment_preference(self, method_name='Safe Charge'):
        if any([self.pair.is_crypto, self.pk, self.payment_preference]):
            return
        self.payment_preference = PaymentPreference.objects.get(
            user__is_staff=True,
            payment_method__name__icontains=method_name
        )

    def save(self, *args, **kwargs):
        self._validate_fields()
        if not self.unique_reference:
            self.unique_reference = \
                self.gen_unique_value(
                    lambda x: self.get_random_unique_reference(x),
                    lambda x: Order.objects.filter(unique_reference=x).count(),
                    settings.UNIQUE_REFERENCE_LENGTH
                )
        if self.pair.quote.code == 'XRP':
            self.destination_tag = \
                self.gen_destination_tag(
                    lambda: self.get_random_integer(),
                    lambda x: Order.objects.filter(destination_tag=x).count()
                )
        if self.pair.is_crypto:
            self.exchange = True
        else:
            self.exchange = False
        if not self.pk:
            if self.amount_base:
                self.calculate_quote_from_base()
            elif self.amount_quote:
                self.calculate_base_from_quote()
        self._validate_order_amount()
        self._validate_price()
        self._validate_reserves()
        super(Order, self).save(*args, **kwargs)

    def calculate_quote_from_base(self, price=None):
        try:
            self.calculate_from(_from='base', price=price)
        except InvalidOperation:
            raise ValidationError(
                _('It is not possible to receive {} {}'.format(
                    self.amount_base,
                    self.pair.base.code
                ))
            )

    def calculate_base_from_quote(self, price=None):
        try:
            self.calculate_from(_from='quote', price=price)
        except InvalidOperation:
            raise ValidationError(
                _('It is not possible to deposit {} {}'.format(
                    self.amount_quote,
                    self.pair.quote.code
                ))
            )

    def set_slippage(self, price, amount, amount_type):
        currency = self.pair.base
        quote = self.pair.quote
        if amount_type == 'base':
            additional_amount = amount
        elif amount_type == 'quote':
            additional_amount = amount / price.rate

        slippage = self.get_current_slippage(
            currency, quote, additional_amount=additional_amount
        )
        self.slippage = slippage
        currency.current_slippage = slippage
        currency.save()
        price.slippage = slippage
        price.save()

    def calculate_from(self, _from='base', price=None):
        self.set_provided_amount_option()
        self.set_payment_preference()
        if _from == 'base':
            _to = 'quote'
        elif _from == 'quote':
            _to = 'base'
        else:
            raise NotImplementedError('Not implemented conversion')
        amount_input = Decimal(getattr(self, 'amount_{}'.format(_from)))
        setattr(self, 'amount_{}'.format(_from), amount_input)
        if not price:
            price = self.pair.latest_price
        self.price = price
        self.set_slippage(self.price, amount_input, _from)
        ticker_amount_output = getattr(self, 'ticker_amount_{}'.format(_to))
        fee_adder = getattr(self, 'add_payment_fee_to_amount_{}'.format(_to))
        amount_output = fee_adder(ticker_amount_output)
        decimal_places = getattr(
            self, 'recommended_{}_decimal_places'.format(_to))
        amount_output_formatted = money_format(amount_output,
                                               places=decimal_places)
        setattr(self, 'amount_{}'.format(_to), amount_output_formatted)

    @property
    def payment_url(self):
        if any([self.pair.quote.is_crypto, self.status != self.INITIAL]):
            return
        return safe_charge_client.generate_cachier_url_for_order(self)

    @cached_property_with_ttl(ttl=settings.TICKER_INTERVAL)
    def amount_eur(self):
        return Price.convert_amount(self.amount_quote,
                                    self.pair.quote, 'EUR')

    @cached_property_with_ttl(ttl=settings.TICKER_INTERVAL)
    def amount_usd(self):
        return Price.convert_amount(self.amount_quote,
                                    self.pair.quote, 'USD')

    @cached_property_with_ttl(ttl=settings.TICKER_INTERVAL)
    def amount_btc(self):
        return Price.convert_amount(self.amount_quote,
                                    self.pair.quote, 'BTC')

    @property
    def ticker_amount_quote(self):
        if not self.price:
            return self.amount_quote
        # For annotations
        res = None
        if self.order_type == Order.BUY:
            res = self.amount_base * self.price.rate
        elif self.order_type == Order.SELL:
            res = self.amount_base * self.price.ticker.bid
        return res

    @property
    def ticker_amount_base(self):
        if not self.price:
            return self.amount_base
        # For annotations
        res = None
        if self.order_type == Order.BUY:
            res = self.amount_quote / self.price.rate
        elif self.order_type == Order.SELL:
            res = self.amount_quote / self.price.ticker.bid
        return res

    @property
    def dynamic_decimal_places(self):
        return False

    @property
    def recommended_quote_decimal_places(self):
        return self.recommended_decimal_places(self.ticker_amount_quote,
                                               self.pair.quote,
                                               dynamic=self.dynamic_decimal_places)  # noqa

    @property
    def recommended_base_decimal_places(self):
        return self.recommended_decimal_places(self.ticker_amount_base,
                                               self.pair.base,
                                               dynamic=self.dynamic_decimal_places)  # noqa

    @property
    def withdrawal_fee(self):
        return self.pair.base.withdrawal_fee

    @property
    def withdrawal_fee_quote(self):
        if self.order_type == self.BUY:
            return self.pair.base.withdrawal_fee * self.price.ticker.ask
        if self.order_type == self.SELL:
            return self.pair.base.withdrawal_fee * self.price.ticker.bid

    def recommended_decimal_places(self, amount, currency, dynamic=False):
        decimal_places = 2
        if currency.is_crypto:
            if dynamic:
                add_places = -int(floor(log10(abs(amount))))
                if add_places > 0:
                    decimal_places += add_places
            else:
                decimal_places = 8
        return decimal_places

    def _get_minimal_payment_method_fee(self, currency):
        payment_method = self.payment_preference.payment_method
        min_fee = payment_method.minimal_fee_amount
        min_curr = payment_method.minimal_fee_currency
        return Price.convert_amount(min_fee, min_curr, currency)

    @property
    def minimal_payment_method_fee_quote(self):
        return self._get_minimal_payment_method_fee(self.pair.quote)

    @property
    def minimal_payment_method_fee_base(self):
        return self.minimal_payment_method_fee_quote / self.price.rate

    def add_payment_fee_to_amount_base(self, amount_base):
        if any([not self.payment_preference, self.pair.is_crypto]):
            res = amount_base
        else:
            method = self.payment_preference.payment_method
            fee = method.fee_deposit
            fee_amount = fee * amount_base
            if fee_amount >= self.minimal_payment_method_fee_base:
                res = amount_base - fee_amount
            else:
                res = amount_base - self.minimal_payment_method_fee_base
        return res - self.withdrawal_fee

    def add_payment_fee_to_amount_quote(self, amount_quote):
        amount_quote += self.withdrawal_fee_quote

        if any([not self.payment_preference, self.pair.is_crypto]):
            return amount_quote

        base = Decimal('1.0')
        fee = Decimal('0.0')
        method = self.payment_preference.payment_method
        if self.order_type == self.BUY:
            fee = method.fee_deposit
            if method.pays_deposit_fee == method.MERCHANT:
                fee = -fee
        elif self.order_type == self.SELL:
            fee = self.payment_preference.payment_method.fee_withdraw
            if method.pays_withdraw_fee == method.MERCHANT:
                fee = -fee
        res = amount_quote / (base - fee)
        if res - amount_quote < self.minimal_payment_method_fee_quote:
            res = amount_quote + self.minimal_payment_method_fee_quote
        return res

    @property
    def coverable(self):
        if self.status not in self.IN_SUCCESS_RELEASED:
            if self.amount_base >= self.pair.base.available_main_reserves:
                return False
        return True

    @property
    def is_paid(self):
        if self.order_type == self.BUY and not self.exchange:
            return self.is_paid_buy
        else:
            raise NotImplementedError('Exists only for BUY orders.')

    @property
    def success_payments_amount(self):
        payments = self.success_payments_by_reference
        if not payments:
            payments = self.success_payments_by_wallet
        sum_success = Decimal(0)
        for p in payments:
            sum_success += p.amount_cash
        return sum_success

    @property
    def success_payments_by_reference(self):
        ref = self.unique_reference
        payments = Payment.objects.filter(
            is_success=True, reference=ref, currency=self.pair.quote)
        return payments

    @property
    def bad_currency_payments(self):
        payments = self.payment_set.filter(~Q(currency=self.pair.quote))
        return payments

    @property
    def success_payments_by_wallet(self):
        method = self.payment_preference.payment_method
        payments = Payment.objects.filter(
            is_success=True,
            user=self.user,
            amount_cash=self.amount_quote,
            payment_preference__payment_method=method,
            currency=self.pair.quote,
        ).filter(Q(order=self) | Q(order=None))
        return payments

    @property
    def is_paid_buy(self):
        sum_all = self.success_payments_amount
        amount_expected = (
            self.amount_quote -
            self.payment_preference.payment_method.allowed_amount_unpaid
        )
        if sum_all >= amount_expected:
            return True
        return False

    @property
    def part_paid_buy(self):
        if self.order_type != self.BUY:
            return False
        sum_all = self.success_payments_amount()
        amount_expected = self.amount_quote
        return sum_all / amount_expected

    @property
    def is_buy(self):
        return self.order_type == self.BUY

    @property
    def requires_withdraw_address(self):
        return (self.order_type == self.BUY) or self.exchange

    @property
    def payment_deadline(self):
        """returns datetime of payment_deadline (creation + payment_window)"""
        # TODO: Use this for pay until message on 'order success' screen
        return self.created_on + timedelta(minutes=self.payment_window)

    @property
    def kyc_deadline(self):
        payment = self.payment_set.last()
        if payment:
            return payment.kyc_void_time

    @property
    def expired(self):
        """Is expired if payment_deadline is exceeded and it's not paid yet"""
        # TODO: validate this business rule
        # TODO: Refactor, it is unreasonable to have different standards of
        # time in the DB
        return (timezone.now() > self.payment_deadline) and \
               (self.status not in Order.IN_PAID + [Order.PAID_UNCONFIRMED])

    @property
    def unpaid_order_expired(self):
        """Is expired when an order has not been payed within 1hr"""
        return (timezone.now() - self.created_on > timedelta(
                minutes=self.unpaid_order_window + self.payment_window)
                ) and (self.status == Order.INITIAL)

    @property
    def payment_status_frozen(self):
        """return a boolean indicating if order can be updated
        Order is frozen if it is expired or has been paid
        """
        # TODO: validate this business rule
        return self.expired or self.status in Order.IN_RELEASED

    @property
    def target(self):
        """return target currency"""
        if self.order_type == self.BUY:
            return self.pair.base.code
        else:
            return self.pair.quote.code

    @property
    def withdrawal_address_frozen(self):
        """return bool whether the withdraw address can
           be changed"""
        return self.status in Order.IN_RELEASED

    @property
    def rate(self):
        return money_format(self.amount_quote / self.amount_base, places=8)

    @property
    def inverted_rate(self):
        return money_format(self.amount_base / self.amount_quote, places=8)

    @property
    def status_name(self):
        return [status for status in Order.STATUS_TYPES if status[0] == self.status]  # noqa

    @classmethod
    def pending_amount_diff(cls, currency, additional_amount=0):
        if not isinstance(additional_amount, Decimal):
            additional_amount = Decimal(str(additional_amount))
        return additional_amount
        # FIXME: only use additional_amount for now, logic down is for reading order list  # noqa
        # if not isinstance(currency, Currency):
        #     currency = Currency.objects.get(code=currency)
        # if not isinstance(additional_amount, Decimal):
        #     additional_amount = Decimal(str(additional_amount))
        # base = cls.objects.filter(
        #     pair__base=currency, status=cls.PAID_UNCONFIRMED).aggregate(
        #     Sum('amount_base'))['amount_base__sum']
        # quote = cls.objects.filter(
        #     pair__quote=currency, status=cls.PAID_UNCONFIRMED).aggregate(
        #     Sum('amount_quote'))['amount_quote__sum']
        # if not base:
        #     base = Decimal('0')
        # base += additional_amount
        # if not quote:
        #     quote = Decimal('0')
        # return base - quote

    @classmethod
    def get_current_slippage(cls, currency, quote, additional_amount=0):
        slippage_rate = \
            currency.slippage_rate * quote.quote_slippage_rate_multiplier  # noqa
        unslippaged_amount = \
            currency.unslippaged_amount * quote.quote_unslippaged_amount_multiplier  # noqa
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        diff = cls.pending_amount_diff(
            currency, additional_amount=additional_amount
        )
        if diff < unslippaged_amount:
            return Decimal('0')
        else:
            return (diff - unslippaged_amount) * slippage_rate  # noqa

    def get_profile(self):
        return self.user.profile

    def notify(self):
        profile = self.get_profile()

        # Activate translation
        if any([profile.notify_by_email, profile.notify_by_phone]):
            activate(profile.lang)

        status_verb = self.get_status_display().lower()
        if self.status == self.INITIAL:
            status_verb = 'created'
        elif self.status == self.PAID_UNCONFIRMED:
            status_verb = 'paid(waiting for confirmation)'

        title = _(
            'Nexchange: Order {ref} {status_verb}'.format(
                ref=self.unique_reference,
                status_verb=status_verb
            )
        )
        msg = _('Your order {ref}: is {status_verb}.').format(
            ref=self.unique_reference,
            status_verb=status_verb
        )
        if self.withdraw_address:
            msg += ' Withdraw address: {withdraw_address}.'.format(
                withdraw_address=self.withdraw_address.address
            )
            withdraw_transaction = self.transactions.filter(
                type=Transaction.WITHDRAW).last()
            if withdraw_transaction is not None:
                tx_id = withdraw_transaction.tx_id
                if tx_id is not None:
                    msg += ' Transaction id: {tx_id}.'.format(
                        tx_id=tx_id)

        # send sms depending on notification settings in profile
        if profile.notify_by_phone and profile.phone:
            phone_to = str(profile.phone)
            send_sms(msg, phone_to)

        # send email
        if profile.notify_by_email and profile.user.email:
            send_email(profile.user.email, title, msg)

    def __str__(self):
        name = \
            '{status} {type} {unique_reference} {pair} {amount_base} {base} ' \
            '{amount_quote} {quote} {username}'.format(
                username=self.user.username,
                type=self.get_order_type_display(),
                pair=self.pair.name,
                amount_base=str(self.amount_base).rstrip('0').rstrip('.'),
                amount_quote=str(self.amount_quote).rstrip('0').rstrip('.'),
                base=self.pair.base.code,
                quote=self.pair.quote.code,
                status=self.get_status_display(),
                unique_reference=self.unique_reference
            )
        return name

    def calculate_order(self, amount_quote, payment_method=None):
        if self.expired:
            price = Price.objects.filter(
                pair=self.pair, market__is_main_market=True).latest('id')
            now = timezone.now()
            if now > self.payment_deadline:
                expired_minutes = ceil(
                    (now - self.payment_deadline).seconds / 60)
            else:
                expired_minutes = 0
            self.payment_window += settings.PAYMENT_WINDOW + expired_minutes
        else:
            price = self.price
        new_payment_method = False
        if payment_method:
            if not self.payment_preference:
                new_payment_method = True
            elif self.payment_preference.payment_method != payment_method:
                new_payment_method = True

        if any([self.expired, self.amount_quote != amount_quote,
                new_payment_method]):
            if new_payment_method:
                self.payment_preference = PaymentPreference.objects.get(
                    user__is_staff=True,
                    payment_method=payment_method
                )
            self.amount_quote = amount_quote
            self.calculate_base_from_quote(price=price)
            self.save()

    @transition(field=status, source=INITIAL, target=PAID_UNCONFIRMED)
    def _register_deposit(self, tx_data, crypto=True):
        if crypto:
            model = Transaction
            amount_key = 'amount'
        else:
            model = Payment
            amount_key = 'amount_cash'
        order = tx_data.get('order')
        tx_type = tx_data.get('type')
        tx_amount = tx_data.get(amount_key)
        tx_currency = tx_data.get('currency')
        if order.pair.quote.code == 'XRP':
            tx_destination_tag = tx_data.get('destination_tag')
            if order.destination_tag != tx_destination_tag:
                raise ValidationError(
                    'Bad tx destination tag {}. Should be {}'.format(
                        order, self
                    )
                )

        if order != self:
            raise ValidationError(
                'Bad order {} on the deposit tx. Should be {}'.format(
                    order, self
                )
            )
        if self.pair.quote != tx_currency:
            raise ValidationError(
                'Bad tx currency {}. Order quote currency {}'.format(
                    tx_currency, self.pair.quote
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
        payment_method = None
        if not crypto:
            payment_method = tx.payment_preference.payment_method

        self.calculate_order(tx_amount, payment_method=payment_method)

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
    def _confirm_deposit(self, tx, crypto=True):
        if crypto:
            success_params = ['is_completed', 'is_verified']
        else:
            success_params = ['is_complete']
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
        self.set_as_paid_on = timezone.now()

    def confirm_deposit(self, tx, crypto=True):
        res = {'status': 'OK'}
        try:
            self._confirm_deposit(tx, crypto=crypto)
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
        self.save()
        return res

    @transition(field=status, source=PAID, target=PRE_RELEASE)
    def _pre_release(self, api=None):
        healthy = api.health_check(self.pair.base)
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
        if currency != self.pair.base or amount != self.amount_base:
            raise ValidationError(
                'Wrong amount {} or currency {} for order {} release'.format(
                    amount, currency, self.unique_reference
                )
            )
        old_withdraw_txs = self.transactions.exclude(
            type__in=[Transaction.DEPOSIT, Transaction.INTERNAL])
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
            tx_id, success = api.release_coins(currency, self.withdraw_address,
                                               amount, payment_id=payment_id,
                                               destination_tag=destination_tag)
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
        else:
            app.send_task(self.RETRY_RELEASE, [tx.pk],
                          countdown=settings.RETRY_RELEASE_TIME)

        return tx

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

    @transition(field=status, source=PAID_UNCONFIRMED, target=CANCELED)
    @transition(field=status, source=INITIAL, target=CANCELED)
    def _cancel(self):
        pass

    def cancel(self):
        res = {'status': 'OK'}
        try:
            self._cancel()
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
            self.flag(val=e)
        self.save()
        return res

    @transition(field=status, source=PRE_RELEASE, target=REFUNDED)
    @transition(field=status, source=PAID, target=REFUNDED)
    def _refund_exchange(self):
        old_withdraw_txs = self.transactions.exclude(
            type__in=[Transaction.DEPOSIT, Transaction.INTERNAL])
        dep_tx = self.transactions.get(type='D')
        dep_tx.flag(val='refunded')
        currency = dep_tx.currency
        amount = dep_tx.amount
        address = self.refund_address
        if currency != self.pair.quote:
            msg = 'DEPOSIT tx currency {} is not the same as order quote {}.' \
                  ' Order {}'.format(dep_tx.currency, self.pair.quote,
                                     self.unique_reference)
            self.flag(val=msg)
            raise ValidationError(msg)
        if amount != self.amount_quote:
            msg = 'DEPOSIT tx amount {} is not the same as order ' \
                  'amount_quote {}. Order {}'.format(amount, self.amount_quote,
                                                     self.unique_reference)
            self.flag(val=msg)
            raise ValidationError(msg)
        if any([not address, address.currency != self.pair.quote,
                address == self.deposit_address]):
            msg = 'Wrong refund address {}.Order {}'.format(
                address, self.unique_reference
            )
            self.flag(val=msg)
            raise ValidationError(msg)
        if len(old_withdraw_txs) == 0 and dep_tx:
            tx = Transaction(
                amount=amount,
                type=Transaction.REFUND,
                currency=currency,
                refunded_transaction=dep_tx,
                address_to=address,
                order=self
            )
            tx.save()
            api = factory.get_api_client(currency.wallet)
            tx_id, success = api.release_coins(currency, address, amount)
            setattr(tx, api.TX_ID_FIELD_NAME, tx_id)
            tx.save()
        else:
            msg = 'Order {} already has WITHDRAW or None type ' \
                  'transactions {}'.format(self, old_withdraw_txs)
            self.flag(val=msg)
            raise ValidationError(msg)

        return tx

    @transition(field=status, source=PAID_UNCONFIRMED, target=REFUNDED)
    def _refund_fiat(self, refund_type='void'):
        payment = self.payment_set.get()
        payment.flag(val=refund_type)
        if not payment.is_success:
            msg = 'Cannot refund order {}. Deposit payment {} is not ' \
                  'successful'.format(self.unique_reference, payment)
            self.flag(val=msg)
            raise ValidationError(msg)
        order = payment.order
        if order != self:
            msg = 'Cannot refund order {}. Payment order {} is not the ' \
                  'same'.format(self.unique_reference, order)
            self.flag(val=msg)
            raise ValidationError(msg)
        params = {
            'currency': payment.currency.code,
            'amount': str(money_format(payment.amount_cash, places=2)),
            'clientRequestId': '{}_{}'.format(refund_type,
                                              order.unique_reference),
            'clientUniqueId': '{}_{}'.format(refund_type,
                                             order.unique_reference),
            'relatedTransactionId': payment.secondary_payment_system_id,
            'authCode': payment.auth_code
        }
        if refund_type == 'refund':
            res = safe_charge_client.api.refundTransaction(**params)
        elif refund_type == 'void':
            res = safe_charge_client.api.voidTransaction(**params)
        status = res.get('transactionStatus', '')
        if status != 'APPROVED':
            msg = 'Cannot refund order {}. Attemp is not approved: {}'.format(
                self.unique_reference, res
            )
            self.flag(val=msg)
            raise ValidationError(msg)
        payment.is_success = False
        payment.save()
        payment.flag(val=res)

    def refund(self, refund_type='void'):
        res = {'status': 'OK'}
        try:
            if self.exchange:
                tx = self._refund_exchange()
                res.update({'tx': tx})
            else:
                self._refund_fiat(refund_type=refund_type)
        except Exception as e:
            res = {'status': 'ERROR', 'message': '{}'.format(e)}
        self.save()
        return res

    @property
    def amount_quote_fee(self):
        if not self.payment_preference:
            return Decimal('0.0')
        fee = self.payment_preference.payment_method.fee_deposit
        return fee * self.amount_quote

    @property
    def token(self):
        order_count = self.user.orders.all().count()
        if order_count > 1:
            return
        try:
            token = AccessToken.objects.filter(user=self.user).latest('id')
        except AccessToken.DoesNotExist:
            return
        if not token or not token.is_valid():
            return
        return token.token

    @property
    def display_refund_address(self):
        if self.status == self.PRE_RELEASE:
            return True
        if self.status == self.PAID:
            if self.set_as_paid_on \
                    and self.set_as_paid_on + \
                    settings.MAX_TIME_TO_RELEASE_INTERVAL < timezone.now():
                return True
        return False

    @property
    def base_destination_tag(self):
        if self.pair.base.code == 'XRP':
            return self.destination_tag

    @property
    def quote_destination_tag(self):
        if self.pair.quote.code == 'XRP':
            return self.destination_tag
