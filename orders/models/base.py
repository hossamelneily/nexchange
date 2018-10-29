
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from core.common.models import SoftDeletableModel, TimeStampedModel,\
    UniqueFieldMixin, FlagableMixin
from audit_log.models import AuthStampedModel
from core.models import Pair
from core.validators import validate_xmr_payment_id, validate_destination_tag


class BaseUserOrder(models.Model):

    class Meta:
        abstract = True

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
    _order_status_help_list = (
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
    _order_status_help = \
        ((len(_order_status_help_list) // 2) * '{} - {}<br/>').format(
            *_order_status_help_list
        )

    BUY = 1
    SELL = 0
    TYPES = (
        (SELL, 'SELL'),
        (BUY, 'BUY'),
    )
    _order_type_help = (2 * '{} - {}<br/>').format(
        _('BUY'), _('Buy base currency ({}).'.format(BUY)),
        _('SELL'), _('Sell base currency ({}).'.format(SELL)),
    )
    order_type = models.IntegerField(
        choices=TYPES, default=BUY, help_text=_order_type_help
    )
    withdraw_address = models.ForeignKey('core.Address',
                                         null=True,
                                         blank=True,
                                         related_name='%(class)s_set_withdraw',
                                         default=None,
                                         on_delete=models.DO_NOTHING)
    deposit_address = models.ForeignKey('core.Address',
                                        null=True,
                                        blank=True,
                                        related_name='%(class)s_set_deposit',
                                        default=None,
                                        on_delete=models.DO_NOTHING)
    refund_address = models.ForeignKey(
        'core.Address', null=True, blank=True,
        related_name='%(class)s_set_refund',
        default=None, on_delete=models.DO_NOTHING
    )
    payment_id = models.CharField(
        max_length=64, null=True, blank=True, default=None,
        validators=[validate_xmr_payment_id]
    )
    destination_tag = models.CharField(
        max_length=10, null=True, blank=True, default=None,
        validators=[validate_destination_tag]
    )
    user = models.ForeignKey(User, related_name='%(class)ss',
                             on_delete=models.DO_NOTHING)
    exchange = models.BooleanField(default=False)

    @property
    def deposit_amount(self):
        if self.order_type == self.BUY:
            return self.amount_quote
        elif self.order_type == self.SELL:
            return self.amount_base

    @property
    def status_name(self):
        return [
            status for status in self.STATUS_TYPES if status[0] == self.status
        ]

    @property
    def withdraw_amount(self):
        if self.order_type == self.BUY:
            return self.amount_base
        elif self.order_type == self.SELL:
            return self.amount_quote

    @property
    def deposit_currency(self):
        if self.order_type == self.BUY:
            return self.pair.quote
        elif self.order_type == self.SELL:
            return self.pair.base

    @property
    def withdraw_currency(self):
        if self.order_type == self.BUY:
            return self.pair.base
        elif self.order_type == self.SELL:
            return self.pair.quote

    @property
    def refund_currency(self):
        return self.deposit_currency

    @property
    def coverable(self):
        if self.status not in self.IN_SUCCESS_RELEASED \
                and self.withdraw_amount >= self.withdraw_currency.\
                available_main_reserves:
            return False
        return True


class BaseOrder(TimeStampedModel, SoftDeletableModel,
                UniqueFieldMixin, FlagableMixin, AuthStampedModel):

    class Meta:
        abstract = True

    amount_base = models.DecimalField(max_digits=18, decimal_places=8,
                                      blank=True)
    amount_quote = models.DecimalField(max_digits=18, decimal_places=8,
                                       blank=True)
    unique_reference = models.CharField(
        max_length=settings.UNIQUE_REFERENCE_MAX_LENGTH)
    admin_comment = models.CharField(max_length=200)

    pair = models.ForeignKey(Pair, on_delete=models.DO_NOTHING)

    @property
    def _rate(self):
        if self.amount_quote and self.amount_base:
            return self.amount_quote / self.amount_base
