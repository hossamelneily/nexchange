from django.db import models
from core.common.models import TimeStampedModel, SoftDeletableModel, Currency

from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField
from ticker.models import Price
from referrals.models import ReferralCode
from .validators import validate_bc


from nexchange.settings import UNIQUE_REFERENCE_LENGTH, PAYMENT_WINDOW,\
    REFERENCE_LOOKUP_ATTEMPTS, SMS_TOKEN_LENGTH, SMS_TOKEN_VALIDITY,\
    SMS_TOKEN_CHARS, MAX_EXPIRED_ORDERS_LIMIT

from django.utils.translation import ugettext_lazy as _
from datetime import timedelta
from django.utils import timezone


class UniqueFieldMixin(models.Model):

    class Meta:
        abstract = True

    @staticmethod
    def gen_unique_value(val_gen, set_len_gen, start_len):
        failed_count = 0
        max_len = start_len
        while True:
            if failed_count >= REFERENCE_LOOKUP_ATTEMPTS:
                failed_count = 0
                max_len += 1

            val = val_gen(max_len)
            cnt_unq = set_len_gen(val)
            if cnt_unq == 0:
                return val
            else:
                failed_count += 1


class ProfileManager(models.Manager):

    def get_by_natural_key(self, username):
        return self.get(user__username=username)


class Profile(TimeStampedModel, SoftDeletableModel):
    objects = ProfileManager()

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = PhoneNumberField(_('Phone'), blank=False, help_text=_(
        'Enter phone number in international format. eg. +555198786543'))
    first_name = models.CharField(max_length=20, blank=True)
    last_name = models.CharField(max_length=20, blank=True)

    def is_banned(self):
        return \
            Order.objects.filter(user=self,
                                 is_paid=True,
                                 expired=True).length \
            > MAX_EXPIRED_ORDERS_LIMIT

    def natural_key(self):
        return self.user.username

    def save(self, *args, **kwargs):
        """Add a SMS token at creation. Used to verify phone number"""
        if self.pk is None:
            token = SmsToken(user=self.user)
            token.save()
        if not self.phone:
            self.phone = self.user.username

        # TODO: move to user class, allow many(?)
        ReferralCode.objects.get_or_create(user=self.user)

        super(Profile, self).save(*args, **kwargs)

User.profile = property(lambda u: Profile.objects.get_or_create(user=u)[0])


class SmsToken(TimeStampedModel, SoftDeletableModel, UniqueFieldMixin):
    sms_token = models.CharField(
        max_length=SMS_TOKEN_LENGTH, blank=True)
    user = models.ForeignKey(User, related_name='sms_token')

    @staticmethod
    def get_sms_token():
        return User.objects.make_random_password(
            length=SMS_TOKEN_LENGTH,
            allowed_chars=SMS_TOKEN_CHARS
        )

    @property
    def valid(self):
        return self.created_on > timezone.now() -\
            timedelta(minutes=SMS_TOKEN_VALIDITY)

    def save(self, *args, **kwargs):
        self.sms_token = self.get_sms_token()
        super(SmsToken, self).save(*args, **kwargs)

    def __str__(self):
        return "{} ({})".format(self.sms_token, self.user.profile.phone)


class PaymentMethodManager(models.Manager):
    def get_by_natural_key(self, bin_code):
        return self.get(bin=bin_code)


class PaymentMethod(TimeStampedModel, SoftDeletableModel):
    BIN_LENGTH = 6
    objects = PaymentMethodManager()
    name = models.CharField(max_length=100)
    handler = models.CharField(max_length=100, null=True)
    bin = models.IntegerField(null=True, default=None)
    fee = models.FloatField(null=True)
    is_slow = models.BooleanField(default=False)
    is_internal = models.BooleanField(default=False)

    def natural_key(self):
        return self.bin

    def __str__(self):
        return "{} ({})".format(self.name, self.bin)


class PaymentPreference(TimeStampedModel, SoftDeletableModel):
    # NULL or Admin for out own (buy adds)
    user = models.ForeignKey(User)
    payment_method = models.ForeignKey(PaymentMethod, default=None)
    currency = models.ManyToManyField(Currency)
    # Optional, sometimes we need this to confirm
    method_owner = models.CharField(max_length=100)
    identifier = models.CharField(max_length=100)
    comment = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.payment_method = self.guess_payment_method()
        super(PaymentPreference, self).save(*args, **kwargs)

    def guess_payment_method(self):
        card_bin = self.identifier[:PaymentMethod.BIN_LENGTH]
        payment_method = []
        while all([self.identifier,
                   not len(payment_method),
                   len(card_bin) > 0]):
            payment_method = PaymentMethod.objects.filter(bin=card_bin)
            card_bin = card_bin[:-1]

        return payment_method[0] if len(payment_method) \
            else PaymentMethod.objects.get(name='Cash')

    def __str__(self):
        return "{} - {} - ({})".format(self.user.profile.phone or
                                       self.user.username,
                                       self.identifier,
                                       self.payment_method.name)


class Order(TimeStampedModel, SoftDeletableModel, UniqueFieldMixin):
    USD = "USD"
    RUB = "RUB"
    BUY = 1
    SELL = 0
    TYPES = (
        (SELL, 'SELL'),
        (BUY, 'BUY'),
    )

    # Todo: inherit from BTC base?
    order_type = models.IntegerField(choices=TYPES, default=BUY)
    amount_cash = models.FloatField()
    amount_btc = models.FloatField()
    currency = models.ForeignKey(Currency)
    payment_window = models.IntegerField(default=PAYMENT_WINDOW)
    user = models.ForeignKey(User)
    is_paid = models.BooleanField(default=False)
    is_released = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    unique_reference = models.CharField(
        max_length=UNIQUE_REFERENCE_LENGTH, unique=True)
    admin_comment = models.CharField(max_length=200)
    payment_preference = models.ForeignKey(PaymentPreference, default=None,
                                           null=True)
    # withdraw_address = models.ForeignKey(Address)

    class Meta:
        ordering = ['-created_on']

    def save(self, *args, **kwargs):
        self.unique_reference = \
            self.gen_unique_value(
                lambda x: get_random_string(x),
                lambda x: Order.objects.filter(unique_reference=x).count(),
                UNIQUE_REFERENCE_LENGTH
            )
        self.convert_coin_to_cash()

        super(Order, self).save(*args, **kwargs)

    def convert_coin_to_cash(self):
        self.amount_btc = float(self.amount_btc)
        queryset = Price.objects.filter().order_by('-id')[:2]
        price_sell = [price for price in queryset if price.type == Price.SELL]
        price_buy = [price for price in queryset if price.type == Price.BUY]

        # Below calculation affect real money the client pays
        assert all([len(price_sell),
                    price_sell[0].price_usd,
                    price_buy[0].price_rub])

        assert all([len(price_buy),
                    price_buy[0].price_usd,
                    price_buy[0].price_rub])

        # TODO: Make this logic more generic,
        # TODO: migrate to using currency through payment_preference

        if self.order_type == Order.SELL and self.currency.code == Order.USD:
            self.amount_cash = self.amount_btc * price_buy[0].price_usd
        elif self.order_type == Order.SELL and self.currency.code == Order.RUB:
            self.amount_cash = self.amount_btc * price_buy[0].price_rub

        if self.order_type == Order.BUY and self.currency.code == Order.USD:
            self.amount_cash = self.amount_btc * price_sell[0].price_usd
        elif self.order_type == Order.BUY and self.currency.code == Order.RUB:
            self.amount_cash = self.amount_btc * price_sell[0].price_rub

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
    def frozen(self):
        """return a boolean indicating if order can be updated
        Order is frozen if it is expired or has been paid
        """
        # TODO: validate this business rule
        return self.expired or self.is_paid

    @property
    def has_withdraw_address(self):
        """return a boolean indicating if order has a withdraw adrress defined
        """
        # TODO: Validate this buisness rule
        return len(self.transaction_set.all()) > 0

    @property
    def withdraw_address(self):
        addr = None

        if self.has_withdraw_address:
            addr = self.transaction_set.first().address_to.address

        return addr

    def __str__(self):
        return "{} {} {} BTC {} {}".format(self.user.username or
                                           self.user.profile.phone,
                                           self.order_type,
                                           self.amount_btc,
                                           self.amount_cash,
                                           self.currency)


class Payment(TimeStampedModel, SoftDeletableModel):
    amount_cash = models.FloatField()
    currency = models.ForeignKey(Currency)
    is_redeemed = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    # Super admin if we are paying for BTC
    user = models.ForeignKey(User)
    # Todo consider one to many for split payments, consider order field on
    # payment
    order = models.ForeignKey(Order, null=True, default=None)


class BtcBase(TimeStampedModel):
    class Meta:
        abstract = True

    WITHDRAW = 'W'
    DEPOSIT = 'D'
    TYPES = (
        (WITHDRAW, 'WITHDRAW'),
        (DEPOSIT, 'DEPOSIT'),
    )
    type = models.CharField(max_length=1, choices=TYPES)


class Address(BtcBase, SoftDeletableModel):
    WITHDRAW = 'W'
    DEPOSIT = 'D'
    TYPES = (
        (WITHDRAW, 'WITHDRAW'),
        (DEPOSIT, 'DEPOSIT'),
    )
    name = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=35, validators=[validate_bc])
    user = models.ForeignKey(User)
    order = models.ForeignKey(Order, null=True, default=None)


class Transaction(BtcBase):
    # null if withdraw from our balance on Kraken
    confirmations = models.IntegerField(default=0)
    tx_id = models.CharField(max_length=35, default=None, null=True)
    address_from = models.ForeignKey(Address, related_name='address_from')
    address_to = models.ForeignKey(Address, related_name='address_to')
    # TODO: how to handle cancellation?
    order = models.ForeignKey(Order)
    is_verified = models.BooleanField(default=False)
