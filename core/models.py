from decimal import Decimal
from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.db import models

from core.common.models import SoftDeletableModel, TimeStampedModel
from core.common.models import FlagableMixin
from .validators import validate_address
from django_countries.fields import CountryField
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import ugettext as _
from core.validators import validate_destination_tag


class BtcBase(TimeStampedModel):

    class Meta:
        abstract = True

    WITHDRAW = 'W'
    DEPOSIT = 'D'
    REFUND = 'R'
    INTERNAL = 'I'
    TYPES = (
        (WITHDRAW, 'WITHDRAW'),
        (DEPOSIT, 'DEPOSIT'),
        (REFUND, 'REFUND'),
        (INTERNAL, 'INTERNAL'),
    )
    type = models.CharField(max_length=1,
                            choices=TYPES, null=True)


class AddressReserve(models.Model):
    card_id = models.CharField('card_id', max_length=36, unique=True,
                               null=True, blank=True, default=None)
    address = models.CharField('address_id', max_length=64, unique=True)
    currency = models.ForeignKey('core.Currency')
    user = models.ForeignKey(User, null=True, blank=True, default=None)
    created = models.DateTimeField(auto_now_add=True)
    disabled = models.BooleanField(default=False)

    def __str__(self):
        return 'User: {}, currency: {}, card_id: {}'.format(
            self.user, self.currency, self.card_id)

    class Meta:
        verbose_name = "Card"
        verbose_name_plural = "Cards"
        ordering = ['-created']


class Address(BtcBase, SoftDeletableModel):
    WITHDRAW = 'W'
    DEPOSIT = 'D'
    INTERNAL = 'I'
    TYPES = (
        (WITHDRAW, 'WITHDRAW'),
        (DEPOSIT, 'DEPOSIT'),
        (INTERNAL, 'INTERNAL'),
    )
    reserve = models.ForeignKey('AddressReserve', null=True,
                                blank=True, default=None, related_name='addr')
    name = models.CharField(max_length=100, blank=True)
    # TODO: what if two different users want to withdraw to the same address?
    address = models.CharField(max_length=127, unique=True,
                               validators=[validate_address])
    user = models.ForeignKey(User, blank=True, null=True)
    currency = models.ForeignKey('core.Currency', blank=True, null=True)
    blocked = models.BooleanField(default=False)

    def __str__(self):
        return '{} {}'.format(self.address, self.name)


class Transaction(BtcBase, FlagableMixin):

    # class Meta:
    #    unique_together = (('amount', 'order', 'type', 'admin_comment'),)

    confirmations = models.IntegerField(default=0)
    tx_id = models.CharField(max_length=100, default=None,
                             null=True, blank=True, unique=True, db_index=True)
    tx_id_api = models.CharField(max_length=55, default=None,
                                 null=True, blank=True, unique=True,
                                 db_index=True)
    address_from = models.ForeignKey(
        'core.Address',
        related_name='txs_from',
        default=None,
        null=True, blank=True)
    address_to = models.ForeignKey('core.Address',
                                   related_name='txs_to')
    # TODO: how to handle cancellation?
    order = models.ForeignKey('orders.Order', related_name='transactions',
                              null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    amount = models.DecimalField(null=False, max_digits=18, decimal_places=8,
                                 default=Decimal('0'), db_index=True)
    # TODO: check if right type is sent by the APIs
    time = models.DateTimeField(null=True, blank=True, default=None)
    currency = models.ForeignKey('core.Currency', related_name='transactions',
                                 null=True, blank=True, default=None)
    admin_comment = models.CharField(max_length=200, null=True, blank=False)
    refunded_transaction = models.ForeignKey(
        'self', null=True, blank=True, default=None
    )
    reserves_cover = models.ForeignKey('risk_management.ReservesCover',
                                       blank=True, null=True)
    destination_tag = models.CharField(
        max_length=10, null=True, blank=True, default=None,
        validators=[validate_destination_tag]
    )

    def _validate_withdraw_txn(self):
        if self.order:
            old_withdraw_txns = self.order.transactions.exclude(
                type=self.DEPOSIT)
            if len(old_withdraw_txns) != 0:
                msg = 'Order {} already has WITHDRAW or None type' \
                      'transactions {}'.format(self.order, old_withdraw_txns)
                self.order.flag(val=msg)
                raise ValidationError(msg)

    def _validate_if_transaction_is_unique(self):
        old_txns = Transaction.objects.filter(
            amount=self.amount, order=self.order, type=self.type,
            admin_comment=self.admin_comment
        )
        if len(old_txns) > 0:
            raise ValidationError(
                'Transaction {} {} {} {} already exists'.format(
                    self.amount, self.type, self.order, self.admin_comment
                )
            )

    def _validate_fields(self):
        if not self.pk:
            # FIXME: remove this after adding unique_together constraint
            if self.type != Transaction.DEPOSIT:
                self._validate_withdraw_txn()
            self._validate_if_transaction_is_unique()

    def save(self, *args, **kwargs):
        self._validate_fields()
        if self.time:
            if isinstance(self.time, int):
                self.time = datetime.fromtimestamp(self.time)
        else:
            self.time = datetime.now(timezone.utc)
        return super(Transaction, self).save(*args, **kwargs)


class CurrencyManager(models.Manager):

    def get_by_natural_key(self, code):

        return self.get(code=code)


class Currency(TimeStampedModel, SoftDeletableModel, FlagableMixin):

    class Meta:
        verbose_name_plural = 'currencies'
    objects = CurrencyManager()
    NATURAL_KEY = 'code'
    code = models.CharField(max_length=4)
    name = models.CharField(max_length=20)
    min_confirmations = \
        models.IntegerField(blank=True, null=True)
    min_confirmation_high = \
        models.IntegerField(blank=True, null=True)
    median_confirmation = models.IntegerField(blank=True, null=True)
    is_crypto = models.BooleanField(default=False)
    withdrawal_fee = models.DecimalField(max_digits=18,
                                         decimal_places=8,
                                         default=0.00)
    wallet = models.CharField(null=True, max_length=10,
                              blank=True, default=None)
    algo = models.CharField(null=True, max_length=15,
                            blank=True, default=None)
    ticker = models.CharField(null=True, max_length=100,
                              blank=True, default=None)
    minimal_amount = models.DecimalField(
        max_digits=18, decimal_places=8,
        default=Decimal('0.01'),
        help_text='Minimal amount that can be set as order base.')

    unslippaged_amount = models.DecimalField(max_digits=18, decimal_places=8,
                                             default=Decimal('1.0'))
    slippage_rate = models.DecimalField(
        max_digits=18, decimal_places=16, default=Decimal('0.0'),
        help_text='slippage per coin, 0.001 means 0.1% per coin'
    )
    quote_slippage_rate_multiplier = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal('1.0'),
        help_text='Multiplies oposite slippage a.k.a in case when this '
                  'currency is quote.'
    )
    quote_unslippaged_amount_multiplier = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal('1.0'),
        help_text='Multiplies opposite unslippaged amount a.k.a in case'
                  'when this currency is quote.'
    )
    current_slippage = models.DecimalField(
        max_digits=18, decimal_places=8, default=Decimal('0'),
    )
    maximal_amount = models.DecimalField(
        max_digits=18, decimal_places=8,
        default=Decimal('1.00'),
        help_text='Maximal amount that can be set as order base.')
    is_token = models.BooleanField(default=False)
    property_id = models.IntegerField(unique=True, null=True, blank=True)
    contract_address = models.CharField(max_length=42, unique=True, null=True,
                                        blank=True)
    decimals = models.IntegerField(default=8)
    execute_cover = models.BooleanField(default=False)

    def get_slippage_amount(self, amount):
        amount_from = amount - self.unslippaged_amount
        if amount_from > Decimal('0'):
            return Decimal('0')
        else:
            return amount_from * self.slippage_rate

    def natural_key(self):
        return self.code

    @property
    def base_pairs(self):
        return Pair.objects.filter(base=self, disabled=False, test_mode=False)

    @property
    def base_pairs_for_test(self):
        return Pair.objects.filter(base=self, disabled=False)

    @property
    def quote_pairs(self):
        return Pair.objects.filter(quote=self, disabled=False, test_mode=False)

    @property
    def quote_pairs_for_test(self):
        return Pair.objects.filter(quote=self, disabled=False)

    @property
    def is_base_of_enabled_pair(self):
        enabled_pairs = self.base_pairs
        if all([len(enabled_pairs) > 0, self.has_enough_reserves]):
            return True
        return False

    @property
    def is_base_of_enabled_pair_for_test(self):
        enabled_pairs = self.base_pairs_for_test
        if len(enabled_pairs) > 0:
            return True
        return False

    @property
    def is_quote_of_enabled_pair(self):
        enabled_pairs = self.quote_pairs
        if all([len(enabled_pairs) > 0, not self.has_too_much_reserves]):
            return True
        return False

    @property
    def is_quote_of_enabled_pair_for_test(self):
        enabled_pairs = self.quote_pairs_for_test
        if len(enabled_pairs) > 0:
            return True
        return False

    @property
    def has_enabled_pairs(self):
        return any([self.is_base_of_enabled_pair,
                    self.is_quote_of_enabled_pair])

    @property
    def has_enabled_pairs_for_test(self):
        return any([self.is_base_of_enabled_pair_for_test,
                    self.is_quote_of_enabled_pair_for_test])

    @property
    def reserve(self):
        try:
            return self.reserve_set.get()
        except ObjectDoesNotExist:
            return

    @property
    def available_reserves(self):
        return getattr(self.reserve, 'available', Decimal('0'))

    @property
    def available_main_reserves(self):
        try:
            return self.reserve_set.get().account_set.\
                get(is_main_account=True).available
        except ObjectDoesNotExist:
            return Decimal('0.0')

    @property
    def current_maximal_amount_to_sell(self):
        if any([self.execute_cover,
                self.available_main_reserves > self.maximal_amount]):
            return self.maximal_amount
        else:
            return self.available_main_reserves

    @property
    def has_enough_reserves(self):
        is_too_low_level = getattr(self.reserve, 'below_minimum_level', False)
        minimum_account_level = getattr(
            self.reserve, 'minimum_main_account_level', Decimal('0')
        )
        return not is_too_low_level and any([
            self.available_main_reserves >= minimum_account_level,
            self.execute_cover
        ])

    @property
    def has_too_much_reserves(self):
        return getattr(self.reserve, 'over_maximum_level', False)

    def __str__(self):
        return self.code


class Market(TimeStampedModel):

    name = models.CharField(null=False, max_length=50, unique=True)
    code = models.CharField(null=False, max_length=10, unique=True)
    is_main_market = models.BooleanField(default=False, max_length=10)

    def save(self, *args, **kwargs):
        if self.is_main_market:
            old_mains = Market.objects.filter(is_main_market=True)
            for old_main in old_mains:
                if self != old_main:
                    old_main.is_main_market = False
                    old_main.save()
        super(Market, self).save(*args, **kwargs)

    def __str__(self):
        return '{}'.format(self.name)


DEFAULT_MARKET_PK = 1


class Pair(TimeStampedModel):

    base = models.ForeignKey(Currency, related_name='base_prices')
    quote = models.ForeignKey(Currency, related_name='quote_prices')
    fee_ask = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0.01'))
    fee_bid = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0.01'))
    name = models.CharField(max_length=8, blank=True, null=True, db_index=True)
    disabled = models.BooleanField(default=False)
    disable_ticker = models.BooleanField(
        default=False, help_text='Opt-out this Pair ticker gathering.'
    )
    test_mode = models.BooleanField(default=True)
    disable_volume = models.BooleanField(
        default=False, help_text='Opt-out this Pair on Volume endpoint.'
    )
    last_price_saved = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.name = '{}{}'.format(self.base, self.quote)
        super(Pair, self).save(*args, **kwargs)

    def __str__(self):
        if self.disabled:
            able = 'Disabled'
        else:
            able = 'Enabled'
        return '{}, {}'.format(self.name, able)

    @property
    def is_crypto(self):
        if self.base.is_crypto and self.quote.is_crypto:
            return True
        return False

    @property
    def contains_token(self):
        if self.base.is_token or self.quote.is_token:
            return True
        return False

    @property
    def reverse_pair(self):
        try:
            return Pair.objects.get(base=self.quote, quote=self.base)
        except self.DoesNotExist:
            return

    def check_currency_disabled(self, currency_type):
        currency = getattr(self, currency_type)
        disabled_currency = getattr(currency, 'disabledcurrency', None)
        disable_with_task = getattr(
            disabled_currency, 'disable_{}'.format(currency_type), False
        )
        disabled = disable_with_task or currency.disabled
        user_reason = getattr(disabled_currency, 'user_visible_reason', None)
        full_reason = '{currency_code}: {user_reason}'.format(
            currency_code=currency.code,
            user_reason=user_reason
        ) if user_reason and disable_with_task else None
        return disabled, full_reason

    def validate_enabled(self):
        error_msg = '{} is not currently a supported Pair.'.format(self.name)
        currency_types = ['base', 'quote']
        disabled_types = []
        for currency_type in currency_types:
            disabled, reason = self.check_currency_disabled(currency_type)
            if disabled:
                error_msg += ' {}'.format(reason) if reason else ''
                disabled_types.append(currency_type)
        if self.disabled or disabled_types:
            raise ValidationError(_(error_msg))

    def validate_user(self, user):
        error_msg = 'Not allowed to use test mode.'
        user.refresh_from_db()
        if self.test_mode and not user.profile.can_use_test_mode:
            raise ValidationError(_(error_msg))

    @property
    def latest_price(self):
        try:
            return \
                self.price_set.filter(market__is_main_market=True).latest('id')
        except ObjectDoesNotExist:
            return

    @property
    def price_expired(self):
        if self.latest_price and not self.latest_price.expired:
            return False
        return True

    def includes_currency(self, currency):
        currencies = [self.base, self.quote]
        currency_codes = [c.code for c in currencies]
        return currency in currencies or currency in currency_codes


class Country(models.Model):
    country = CountryField(unique=True)

    def __str__(self):
        return '{}({})'.format(self.country.name, self.country.code)


class Location(TimeStampedModel, SoftDeletableModel):
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    zip = models.CharField(max_length=10)
    country = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(User)

    def full_address(self):
        return "{}, {}, {}"\
            .format(self.address1, self.city, self.zip)

    def __str__(self):
        return "{} {}: {}".format(
            self.firstname, self.lastname, self.full_address()
        )


class TransactionApiMapper(TimeStampedModel):
    node = models.CharField(null=False, max_length=100)
    start = models.IntegerField(null=True, blank=True, default=0)
