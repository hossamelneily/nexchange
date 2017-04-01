from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from core.common.models import SoftDeletableModel, TimeStampedModel
from core.common.models import FlagableMixin
from .validators import validate_address


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


class Address(BtcBase, SoftDeletableModel):
    WITHDRAW = 'W'
    DEPOSIT = 'D'
    TYPES = (
        (WITHDRAW, 'WITHDRAW'),
        (DEPOSIT, 'DEPOSIT'),
    )
    name = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=42, validators=[validate_address])
    user = models.ForeignKey(User)
    currency = models.ForeignKey('core.Currency', blank=True, null=True)

    def __str__(self):
        return '{} {}'.format(self.address, self.name)


class Transaction(BtcBase):
    confirmations = models.IntegerField(default=0)
    tx_id = models.CharField(max_length=65, default=None,
                             null=True, unique=True)
    tx_id_api = models.CharField(max_length=55, default=None,
                                 null=True, unique=True)
    address_from = models.ForeignKey(
        'core.Address',
        related_name='address_from',
        default=None,
        null=True)
    address_to = models.ForeignKey('core.Address',
                                   related_name='address_to')
    # TODO: how to handle cancellation?
    order = models.ForeignKey('orders.Order', related_name='transactions')
    is_verified = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)


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
    is_crypto = models.BooleanField(default=False)
    fee_offset = models.FloatField(default=0.0)

    def natural_key(self):
        return self.code

    def __str__(self):
        return self.name


class Pair(TimeStampedModel):

    base = models.ForeignKey(Currency, related_name='base_prices')
    quote = models.ForeignKey(Currency, related_name='quote_prices')
    fee_ask = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0.01'))
    fee_bid = models.DecimalField(max_digits=18, decimal_places=8,
                                  default=Decimal('0.01'))
    name = models.CharField(max_length=8, blank=True, null=True)
    disabled = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.name = '{}{}'.format(self.base, self.quote)
        super(Pair, self).save(*args, **kwargs)

    def __str__(self):
        if self.disabled:
            able = 'Disabled'
        else:
            able = 'Ebabled'
        return '{}, {}'.format(self.name, able)

    def kraken_format(self, code, is_crypto):
        if code == 'BTC':
            code = 'XBT'
        if is_crypto:
            res = 'X{}'.format(code)
        else:
            res = 'Z{}'.format(code)
        return res

    @property
    def kraken_style(self):
        base = self.kraken_format(self.base.code, self.base.is_crypto)
        quote = self.kraken_format(self.quote.code, self.quote.is_crypto)
        return '{}{}'.format(base, quote)

    @property
    def invert_kraken_style(self):
        base = self.kraken_format(self.quote.code, self.quote.is_crypto)
        quote = self.kraken_format(self.base.code, self.base.is_crypto)
        return '{}{}'.format(base, quote)

    @property
    def is_crypto(self):
        if self.base.is_crypto and self.quote.is_crypto:
            return True
        return False
