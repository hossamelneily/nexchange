from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from core.common.models import (SoftDeletableModel, TimeStampedModel,
                                UniqueFieldMixin, FlagableMixin)
from core.models import Pair
from payments.utils import money_format
from ticker.models import Price
from django.core.exceptions import ValidationError


class Order(TimeStampedModel, SoftDeletableModel,
            UniqueFieldMixin, FlagableMixin):
    USD = "USD"
    RUB = "RUB"
    EUR = "EUR"
    BTC = "BTC"

    EXCHANGE = 2
    BUY = 1
    SELL = 0
    TYPES = (
        (SELL, 'SELL'),
        (BUY, 'BUY'),
        (EXCHANGE, 'EXCHANGE'),
    )
    _order_type_help = (2 * '{} - {}<br/>' + '{} - {}.').format(
        'BUY', 'Customer is giving fiat, and getting crypto money.',
        'SELL', 'Customer is giving crypto and getting fiat money',
        'EXCHANGE', 'Customer is exchanging different kinds of crypto '
                    'currencies'
    )

    PAID_UNCONFIRMED = -1
    CANCELED = 0
    INITIAL = 1
    PAID = 2
    RELEASED = 3
    COMPLETED = 4
    STATUS_TYPES = (
        (PAID_UNCONFIRMED, 'UNCONFIRMED PAYMENT'),
        (CANCELED, 'CANCELED'),
        (INITIAL, 'INITIAL'),
        (PAID, 'PAID'),
        (RELEASED, 'RELEASED'),
        (COMPLETED, 'COMPLETED'),
    )
    IN_PAID = [PAID, RELEASED, COMPLETED]
    IN_RELEASED = [RELEASED, COMPLETED]
    _could_be_paid_msg = 'Could be paid by crypto transaction or fiat ' \
                         'payment, depending on order_type.'
    _order_status_help = (5 * '{} - {}<br/>' + '{} - {}.').format(
        'INITIAL', 'Initial status of the order.',
        'PAID', 'Order is Paid by customer. ' + _could_be_paid_msg,
        'PAID_UNCONFIRMED', 'Order is possibly paid (unconfirmed crypto '
                            'transaction or fiat payment is to small to '
                            'cover the order.)',
        'RELEASED', 'Order is paid by service provider. ' + _could_be_paid_msg,
        'COMPLETED', 'All statuses of the order is completed',
        'CANCELED', 'Order is canceled.'
    )

    # Todo: inherit from BTC base?, move lengths to settings?
    order_type = models.IntegerField(
        choices=TYPES, default=BUY, help_text=_order_type_help
    )
    status = models.IntegerField(choices=STATUS_TYPES, default=INITIAL,
                                 help_text=_order_status_help)
    amount_base = models.DecimalField(max_digits=18, decimal_places=8)
    amount_quote = models.DecimalField(max_digits=18, decimal_places=8)
    payment_window = models.IntegerField(default=settings.PAYMENT_WINDOW)
    user = models.ForeignKey(User, related_name='orders')
    unique_reference = models.CharField(
        max_length=settings.UNIQUE_REFERENCE_MAX_LENGTH)
    admin_comment = models.CharField(max_length=200)
    payment_preference = models.ForeignKey('payments.PaymentPreference',
                                           default=None,
                                           null=True)
    withdraw_address = models.ForeignKey('core.Address',
                                         null=True,
                                         related_name='order_set',
                                         default=None)
    is_default_rule = models.BooleanField(default=False)
    from_default_rule = models.BooleanField(default=False)
    pair = models.ForeignKey(Pair)
    price = models.ForeignKey(Price, null=True, blank=True)
    user_marked_as_paid = models.BooleanField(default=False)
    system_marked_as_paid = models.BooleanField(default=False)

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

    def _types_range_constrain(self, field, types):
        """ This is used for validating IntegerField's with choices.
        Assures that value is in range of choices.
        """
        if field > max([i[0] for i in types]):
            raise ValidationError(_('Invalid order type choice'))
        elif field < min([i[0] for i in types]):
            raise ValidationError(_('Invalid order type choice'))

    def _validate_fields(self):
        self._types_range_constrain(self.order_type, self.TYPES)
        self._types_range_constrain(self.status, self.STATUS_TYPES)

    def clean(self, *args, **kwargs):
        self._validate_fields()
        super(Order, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self._validate_fields()
        if not self.unique_reference:
            self.unique_reference = \
                self.gen_unique_value(
                    lambda x: get_random_string(x),
                    lambda x: Order.objects.filter(unique_reference=x).count(),
                    settings.UNIQUE_REFERENCE_LENGTH
                )
        if self.status == self.INITIAL:
            self.convert_coin_to_cash()

        super(Order, self).save(*args, **kwargs)

    def _not_supported_exchange_msg(self):
        msg = _('Sorry, we cannot convert {} to {}'.format(
            self.currency_from.code, self.currency_to.code
        ))
        return msg

    def convert_coin_to_cash(self):
        self.amount_base = Decimal(self.amount_base)
        price = Price.objects.filter(pair=self.pair).last()
        self.price = price
        # For annotations
        amount_quote = None
        if self.order_type == Order.BUY:
            amount_quote = self.amount_base * price.ticker.ask
        elif self.order_type == Order.SELL:
            amount_quote = self.amount_base * price.ticker.bid
        self.amount_quote = money_format(amount_quote)

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
        return (timezone.now() > self.payment_deadline) and (
            self.status not in Order.IN_PAID)

    @property
    def payment_status_frozen(self):
        """return a boolean indicating if order can be updated
        Order is frozen if it is expired or has been paid
        """
        # TODO: validate this business rule
        return self.expired or self.status in Order.IN_RELEASED

    @property
    def withdrawal_address_frozen(self):
        """return bool whether the withdraw address can
           be changed"""
        return self.status in Order.IN_RELEASED

    def __str__(self):
        return "{} {} pair:{} base:{} quote:{} status:{}".format(
            self.user.username or self.user.profile.phone,
            self.get_order_type_display(),
            self.pair.name,
            self.amount_base,
            self.amount_quote,
            self.get_status_display()
        )
