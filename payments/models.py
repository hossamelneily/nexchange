from django.contrib.auth.models import User
from django.db import models

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from core.common.models import SoftDeletableModel, \
    TimeStampedModel, FlagableMixin
from core.models import Location


class PaymentMethodManager(models.Manager):

    def get_by_natural_key(self, bin_code):
        return self.get(bin=bin_code)


class PaymentMethod(TimeStampedModel, SoftDeletableModel):
    NATURAL_KEY = 'bin'

    CUSTOMER = 0
    MERCHANT = 1

    USERS = (
        (CUSTOMER, 'CUSTOMER'),
        (MERCHANT, 'MERCHANT'),
    )

    MANUAL = 0
    AUTO = 1
    MANUAL_AND_AUTO = 2
    ON_ORDER_SUCCESS_MODAL = 3
    CHECKOUT_TYPES = (
        (MANUAL, 'MANUAL'),
        (AUTO, 'AUTO'),
        (MANUAL_AND_AUTO, 'MANUAL & AUTO'),
        (ON_ORDER_SUCCESS_MODAL, 'Checkout on Order Success'),
    )

    METHODS_NAMES_WITH_BANK_DETAILS = ['SEPA', 'SWIFT']
    BIN_LENGTH = 6
    objects = PaymentMethodManager()
    name = models.CharField(max_length=100)
    handler = models.CharField(max_length=100, null=True)
    bin = models.IntegerField(null=True, default=None)
    fee_deposit = models.DecimalField(max_digits=5, decimal_places=3,
                                      null=True, blank=True, default=0)
    fee_withdraw = models.DecimalField(max_digits=5, decimal_places=3,
                                       null=True, blank=True, default=0)
    is_slow = models.BooleanField(default=False)
    payment_window = models
    is_internal = models.BooleanField(default=False)
    pays_withdraw_fee = models.IntegerField(
        choices=USERS, default=MERCHANT
    )
    pays_deposit_fee = models.IntegerField(
        choices=USERS, default=CUSTOMER
    )
    allowed_amount_unpaid = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.01,
        help_text='Allowed difference between order amount (ticker_amount) '
                  'and payment amount (amount_cash).'
    )
    checkout_type = models.IntegerField(
        choices=CHECKOUT_TYPES, default=MANUAL
    )

    @property
    def auto_checkout(self):
        if self.checkout_type in [self.AUTO, self.MANUAL_AND_AUTO]:
            return True
        return False

    @property
    def manual_checkout(self):
        if self.checkout_type in [self.MANUAL, self.MANUAL_AND_AUTO]:
            return True
        return False

    @property
    def on_order_success_modal_checkout(self):
        if self.checkout_type in [self.ON_ORDER_SUCCESS_MODAL]:
            return True
        return False

    def natural_key(self):
        return self.bin

    def __str__(self):
        return "{} ({})".format(self.name, self.bin)


class PaymentPreference(TimeStampedModel, SoftDeletableModel, FlagableMixin):
    class Meta:
        unique_together = ('user', 'identifier', 'payment_method')
    # NULL or Admin for out own (buy adds)
    buy_enabled = models.BooleanField(default=True)
    sell_enabled = models.BooleanField(default=True)
    user = models.ForeignKey(User, default=None, blank=True, null=True)
    payment_method = models.ForeignKey('PaymentMethod', default=None)
    currency = models.ManyToManyField('core.Currency')
    # Optional, sometimes we need this to confirm
    identifier = models.CharField(max_length=100)
    secondary_identifier = models.CharField(max_length=100,
                                            default=None,
                                            null=True,
                                            blank=True)
    comment = models.CharField(max_length=255, default=None,
                               blank=True, null=True)
    name = models.CharField(max_length=100, null=True,
                            blank=True, default=None)
    beneficiary = models.CharField(max_length=100, null=True,
                                   blank=True, default=None)
    bic = models.CharField(max_length=100, null=True,
                           blank=True, default=None)
    ccexp = models.CharField(max_length=5, null=True, blank=True, default=None)
    cvv = models.CharField(max_length=4, null=True, blank=True, default=None)
    physical_address_bank = models.CharField(max_length=255, null=True,
                                             blank=True, default=None)
    # If exists, overrides the address save in the profile of the owner
    physical_address_owner = models.CharField(max_length=255, null=True,
                                              blank=True, default=None)
    location = models.ForeignKey(Location, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not hasattr(self, 'payment_method'):
            self.payment_method = self.guess_payment_method()
        super(PaymentPreference, self).save(*args, **kwargs)

    def guess_payment_method(self):
        identifier = ''.join(self.identifier.split(' '))
        card_bin = identifier[:PaymentMethod.BIN_LENGTH]
        payment_method = []
        while all([identifier,
                   not len(payment_method),
                   len(card_bin) > 0]):
            payment_method = PaymentMethod.objects.filter(bin=card_bin)
            card_bin = card_bin[:-1]

        return payment_method[0] if len(payment_method) \
            else PaymentMethod.objects.get(name='Cash')

    def __str__(self):
        return "{} {}".format(self.payment_method.name,
                              self.identifier)


class Payment(TimeStampedModel, SoftDeletableModel, FlagableMixin):
    nonce = models.CharField(_('Nonce'),
                             max_length=256,
                             null=True,
                             blank=True)
    amount_cash = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.ForeignKey('core.Currency', default=None)
    is_redeemed = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    is_success = models.BooleanField(default=False)
    payment_preference = models.ForeignKey('PaymentPreference',
                                           null=False, default=None)
    # Super admin if we are paying for BTC
    user = models.ForeignKey(User, default=None, null=True, blank=True)
    # Todo consider one to many for split payments, consider order field on
    # payment
    order = models.ForeignKey('orders.Order', null=True, default=None)
    reference = models.CharField(max_length=255,
                                 null=True, default=None)
    comment = models.CharField(max_length=255,
                               null=True, default=None)
    payment_system_id = models.CharField(max_length=255, unique=True,
                                         null=True, default=None)

    @property
    def api_time(self):
        safe_time = self.created_on - settings.PAYMENT_WINDOW_SAFETY_INTERVAL
        return safe_time.__format__('%Y-%m-%d %H:%M:%S')

    @property
    def api_time_iso_8601(self):
        safe_time = self.created_on - settings.PAYMENT_WINDOW_SAFETY_INTERVAL
        return safe_time.__format__('%Y-%m-%dT%H:%M:%S+00:00')

    def __str__(self):
        return '{} {} - {}'.format(self.amount_cash,
                                   self.currency,
                                   self.payment_preference)


class PaymentCredentials(TimeStampedModel, SoftDeletableModel):
    payment_preference = models.ForeignKey('PaymentPreference')
    uni = models.CharField(_('Uni'), max_length=60,
                           null=True, blank=True)
    nonce = models.CharField(_('Nonce'), max_length=256,
                             null=True, blank=True)
    token = models.CharField(_('Token'), max_length=256,
                             null=True, blank=True)
    is_default = models.BooleanField(_('Default'), default=False)
    is_delete = models.BooleanField(_('Delete'), default=False)

    def __str__(self):
        pref = self.paymentpreference_set.get()
        return "{0} - ({1})".format(pref.user.username,
                                    pref.identifier)


# TODO: Move to core
class UserCards(models.Model):
    TYPES = (
        ('BTC', 'BTC'),
        ('LTC', 'LTC'),
        ('ETH', 'ETH'),
    )
    card_id = models.CharField('Card_id', max_length=36)
    address_id = models.CharField('Address_id', max_length=42)
    currency = models.CharField('Currency', choices=TYPES, max_length=3)
    user = models.ForeignKey(User, null=True, blank=True, default=None)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.card_id

    class Meta:
        verbose_name = "Card"
        verbose_name_plural = "Cards"
        ordering = ['-created']


class FailedRequest(TimeStampedModel):

    url = models.TextField(null=True, blank=True)
    response = models.TextField(null=True, blank=True)
    payload = models.TextField(null=True, blank=True)
    validation_error = models.TextField(null=True, blank=True)
    order = models.ForeignKey('orders.Order')
