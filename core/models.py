from django.contrib.auth.models import User
from django.db import models

from core.common.models import SoftDeletableModel, TimeStampedModel

from .validators import validate_bc


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
    address = models.CharField(max_length=42, validators=[validate_bc])
    user = models.ForeignKey(User)

    def __str__(self):
        return '{} {}'.format(self.address, self.name)


class Transaction(BtcBase):
    confirmations = models.IntegerField(default=0)
    tx_id = models.CharField(max_length=65, default=None, null=True)
    tx_id_api = models.CharField(max_length=55, default=None, null=True)
    address_from = models.ForeignKey(
        'core.Address',
        related_name='address_from',
        default=None,
        null=True)
    address_to = models.ForeignKey('core.Address',
                                   related_name='address_to')
    # TODO: how to handle cancellation?
    order = models.ForeignKey('orders.Order')
    is_verified = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)


class CurrencyManager(models.Manager):

    def get_by_natural_key(self, code):
        return self.get(code=code)


class Currency(TimeStampedModel, SoftDeletableModel):
    objects = CurrencyManager()
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=10)
    min_confirmations = \
        models.IntegerField(blank=True, null=True)
    min_confirmation_high = \
        models.IntegerField(blank=True, null=True)
    is_crypto = models.BooleanField(default=False)

    def natural_key(self):
        return self.code

    def __str__(self):
        return self.name
