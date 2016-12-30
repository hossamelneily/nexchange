from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from core.common.models import (SoftDeletableModel, TimeStampedModel,
                                UniqueFieldMixin)
from core.models import Currency
from payments.utils import money_format
from ticker.models import Price


class Order(TimeStampedModel, SoftDeletableModel, UniqueFieldMixin):
    USD = "USD"
    RUB = "RUB"
    EUR = "EUR"

    BUY = 1
    SELL = 0
    TYPES = (
        (SELL, 'SELL'),
        (BUY, 'BUY'),
    )

    # Todo: inherit from BTC base?, move lengths to settings?
    order_type = models.IntegerField(choices=TYPES, default=BUY)
    amount_cash = models.DecimalField(max_digits=12, decimal_places=2)
    amount_btc = models.DecimalField(max_digits=18, decimal_places=8)
    currency = models.ForeignKey(Currency)
    payment_window = models.IntegerField(default=settings.PAYMENT_WINDOW)
    user = models.ForeignKey(User, related_name='orders')
    is_paid = models.BooleanField(default=False)
    is_released = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    is_failed = models.BooleanField(default=False)
    unique_reference = models.CharField(
        max_length=settings.UNIQUE_REFERENCE_LENGTH, unique=True)
    admin_comment = models.CharField(max_length=200)
    payment_preference = models.ForeignKey('payments.PaymentPreference',
                                           default=None,
                                           null=True)
    withdraw_address = models.ForeignKey('core.Address',
                                         null=True,
                                         related_name='order_set',
                                         default=None)

    class Meta:
        ordering = ['-created_on']

    def save(self, *args, **kwargs):
        self.unique_reference = \
            self.gen_unique_value(
                lambda x: get_random_string(x),
                lambda x: Order.objects.filter(unique_reference=x).count(),
                settings.UNIQUE_REFERENCE_LENGTH
            )
        self.convert_coin_to_cash()

        if 'is_completed' in kwargs and\
                kwargs['is_completed'] and\
                not self.is_completed:
            self.old_referral_revenue = \
                self.user.referral_set.get().revenue

        super(Order, self).save(*args, **kwargs)

    def convert_coin_to_cash(self):
        self.amount_btc = Decimal(self.amount_btc)
        queryset = Price.objects.filter().order_by('-id')[:2]
        price_sell = [price for price in queryset if price.type == Price.SELL]
        price_buy = [price for price in queryset if price.type == Price.BUY]

        # Below calculation affect real money the client pays
        assert all([len(price_sell),
                    price_sell[0].price_usd,
                    price_buy[0].price_rub,
                    price_buy[0].price_eur])

        assert all([len(price_buy),
                    price_buy[0].price_usd,
                    price_buy[0].price_rub,
                    price_buy[0].price_eur])

        # TODO: Make this logic more generic,
        # TODO: migrate to using currency through payment_preference

        # SELL
        self.amount_cash = Decimal(self.amount_btc)

        if self.order_type == Order.SELL and self.currency.code == Order.USD:
            self.amount_cash *= price_buy[0].price_usd

        elif self.order_type == Order.SELL and self.currency.code == Order.RUB:
            self.amount_cash *= price_buy[0].price_rub

        elif self.order_type == Order.SELL and self.currency.code == Order.EUR:
            self.amount_cash *= price_buy[0].price_eur

        # BUY
        if self.order_type == Order.BUY and self.currency.code == Order.USD:
            self.amount_cash *= price_sell[0].price_usd

        elif self.order_type == Order.BUY and self.currency.code == Order.RUB:
            self.amount_cash *= price_sell[0].price_rub

        elif self.order_type == Order.BUY and self.currency.code == Order.EUR:
            self.amount_cash *= price_sell[0].price_eur

        self.amount_cash = money_format(self.amount_cash)

    @property
    def is_buy(self):
        return self.order_type

    @property
    def payment_deadline(self):
        """returns datetime of payment_deadline (creation + payment_window)"""
        # TODO: Use this for pay until message on 'order success' screen
        return self.created_on + timedelta(minutes=self.payment_window)

    @property
    def expired(self):
        """Is expired if payment_deadline is exceeded and it's not paid yet"""
        # TODO: validate this business rule
        # TODO: Refactor, it is unreasonable to have different standards of
        # time in the DB
        return (timezone.now() > self.payment_deadline) and\
               (not self.is_paid) and not self.is_released

    @property
    def payment_status_frozen(self):
        """return a boolean indicating if order can be updated
        Order is frozen if it is expired or has been paid
        """
        # TODO: validate this business rule
        return self.expired or \
            (self.is_paid and
             self.payment_set.last() and
             self.payment_set.last().
             payment_preference.
             payment_method.is_internal)

    @property
    def withdrawal_address_frozen(self):
        """return bool whether the withdraw address can
           be changed"""
        return self.is_released

    def __str__(self):
        return "{} {} {} BTC {} {}".format(self.user.username or
                                           self.user.profile.phone,
                                           self.order_type,
                                           self.amount_btc,
                                           self.amount_cash,
                                           self.currency)
