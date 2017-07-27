from decimal import Decimal
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models

from core.common.models import SoftDeletableModel, TimeStampedModel
from core.common.models import FlagableMixin
from .validators import validate_address
from django_countries.fields import CountryField


class BtcBase(TimeStampedModel):

    class Meta:
        abstract = True

    WITHDRAW = 'W'
    DEPOSIT = 'D'
    TYPES = (
        (WITHDRAW, 'WITHDRAW'),
        (DEPOSIT, 'DEPOSIT'),
    )
    type = models.CharField(max_length=1,
                            choices=TYPES)


class AddressReserve(models.Model):
    card_id = models.CharField('card_id', max_length=36, unique=True,
                               null=True, blank=True, default=None)
    address = models.CharField('address_id', max_length=42, unique=True)
    currency = models.ForeignKey('core.Currency')
    user = models.ForeignKey(User, null=True, blank=True, default=None)
    created = models.DateTimeField(auto_now_add=True)
    disabled = models.BooleanField(default=False)
    need_balance_check = models.BooleanField(default=True)

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
    TYPES = (
        (WITHDRAW, 'WITHDRAW'),
        (DEPOSIT, 'DEPOSIT'),
    )
    reserve = models.ForeignKey('AddressReserve', null=True,
                                blank=True, default=None, related_name='addr')
    name = models.CharField(max_length=100, blank=True)
    # TODO: what if two different users want to withdraw to the same address?
    address = models.CharField(max_length=42, unique=True,
                               validators=[validate_address])
    user = models.ForeignKey(User, blank=True, null=True)
    currency = models.ForeignKey('core.Currency', blank=True, null=True)

    def __str__(self):
        return '{} {}'.format(self.address, self.name)


class Transaction(BtcBase):
    confirmations = models.IntegerField(default=0)
    tx_id = models.CharField(max_length=100, default=None,
                             null=True, unique=True)
    tx_id_api = models.CharField(max_length=55, default=None,
                                 null=True, unique=True)
    address_from = models.ForeignKey(
        'core.Address',
        related_name='txs_from',
        default=None,
        null=True)
    address_to = models.ForeignKey('core.Address',
                                   related_name='txs_to')
    # TODO: how to handle cancellation?
    order = models.ForeignKey('orders.Order', related_name='transactions')
    is_verified = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    amount = models.DecimalField(null=False, max_digits=18, decimal_places=8,
                                 default=Decimal('0.01'))
    # TODO: check if right type is sent by the APIs
    time = models.DateTimeField(null=True, blank=True, default=None)
    currency = models.ForeignKey('core.Currency', related_name='transactions',
                                 null=True, blank=True, default=None)

    def save(self, *args, **kwargs):
        if self.time:
            if isinstance(self.time, int):
                self.time = datetime.fromtimestamp(self.time)
        return super(Transaction, self).save(*args, **kwargs)


class CurrencyManager(models.Manager):

    def get_by_natural_key(self, code):
        return self.get(code=code)


class Currency(TimeStampedModel, SoftDeletableModel, FlagableMixin):
    objects = CurrencyManager()
    NATURAL_KEY = 'code'
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=10)
    min_confirmations = \
        models.IntegerField(blank=True, null=True)
    min_confirmation_high = \
        models.IntegerField(blank=True, null=True)
    median_confirmation = models.IntegerField(blank=True, null=True)
    is_crypto = models.BooleanField(default=False)
    fee_offset = models.FloatField(default=0.0)
    wallet = models.CharField(null=True, max_length=10,
                              blank=True, default=None)
    algo = models.CharField(null=True, max_length=10,
                            blank=True, default=None)
    ticker = models.CharField(null=True, max_length=20,
                              blank=True, default=None)
    minimal_amount = models.DecimalField(
        max_digits=18, decimal_places=8,
        default=Decimal('0.01'),
        help_text='Minimal amount that can be set as order base.')

    def natural_key(self):
        return self.code

    @property
    def base_pairs(self):
        return Pair.objects.filter(base=self, disabled=False)

    @property
    def quote_pairs(self):
        return Pair.objects.filter(quote=self, disabled=False)

    @property
    def is_base_of_enabled_pair(self):
        enabled_pairs = self.base_pairs
        if len(enabled_pairs) > 0:
            return True
        return False

    @property
    def is_quote_of_enabled_pair(self):
        enabled_pairs = self.quote_pairs
        if len(enabled_pairs) > 0:
            return True
        return False

    @property
    def has_enabled_pairs(self):
        return self.is_base_of_enabled_pair or self.is_quote_of_enabled_pair

    def __str__(self):
        return self.code


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

    def save(self, *args, **kwargs):
        self.name = '{}{}'.format(self.base, self.quote)
        super(Pair, self).save(*args, **kwargs)

    def __str__(self):
        if self.disabled:
            able = 'Disabled'
        else:
            able = 'Ebabled'
        return '{}, {}'.format(self.name, able)

    @property
    def is_crypto(self):
        if self.base.is_crypto and self.quote.is_crypto:
            return True
        return False


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
