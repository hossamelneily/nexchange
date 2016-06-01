from django.db import models

from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField

from safedelete import safedelete_mixin_factory, SOFT_DELETE, \
    DELETED_VISIBLE_BY_PK, safedelete_manager_factory, DELETED_INVISIBLE

from nexchange.settings import UNIQUE_REFERENCE_LENGTH, PAYMENT_WINDOW,\
    REFERENCE_LOOKUP_ATTEMPS, SMS_TOKEN_LENGTH

from .validators import validate_bc
from django.utils.translation import ugettext_lazy as _
from datetime import timedelta
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


SoftDeleteMixin = safedelete_mixin_factory(policy=SOFT_DELETE,
                                           visibility=DELETED_VISIBLE_BY_PK)


class SoftDeletableModel(SoftDeleteMixin):
    disabled = models.BooleanField(default=False)
    active_objects = safedelete_manager_factory(
        models.Manager, models.QuerySet, DELETED_INVISIBLE)()

    class Meta:
        abstract = True


class Profile(TimeStampedModel, SoftDeletableModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = PhoneNumberField(blank=False, help_text=_(
        'Enter phone number in international format. eg. +555198786543'))
    first_name = models.CharField(max_length=20, blank=True)
    last_name = models.CharField(max_length=20, blank=True)

    def save(self, *args, **kwargs):
        '''Add a SMS token at creation. Used to verify phone number'''
        if self.pk is None:
            token = SmsToken(user=self.user)
            token.save()
        if not self.phone:
            self.phone = self.user.username

        super(Profile, self).save(*args, **kwargs)

User.profile = property(lambda u: Profile.objects.get_or_create(user=u)[0])


class SmsToken(TimeStampedModel, SoftDeletableModel):
    sms_token = models.CharField(
        max_length=SMS_TOKEN_LENGTH, blank=True)
    user = models.ForeignKey(User, related_name='sms_token')

    def save(self, *args, **kwargs):
        self.sms_token =\
            User.objects.make_random_password(length=4,
                                              allowed_chars='1234567890')
        super(SmsToken, self).save(*args, **kwargs)


class Currency(TimeStampedModel, SoftDeletableModel):
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Order(TimeStampedModel, SoftDeletableModel):
    # Todo: inherit from BTC base?
    amount_cash = models.FloatField()
    amount_btc = models.FloatField()
    currency = models.ForeignKey(Currency)
    payment_window = models.IntegerField(default=PAYMENT_WINDOW)
    user = models.ForeignKey(User)
    is_paid = models.BooleanField(default=False)
    is_released = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    unique_reference = models.CharField(
        max_length=UNIQUE_REFERENCE_LENGTH, unique=True)
    admin_comment = models.CharField(max_length=200)

    class Meta:
        ordering = ['-created_on']

    def save(self, *args, **kwargs):
        unq = True
        failed_count = 0
        MX_LENGTH = UNIQUE_REFERENCE_LENGTH
        while unq:

            if failed_count >= REFERENCE_LOOKUP_ATTEMPS:
                MX_LENGTH += 1

            self.unique_reference = get_random_string(
                length=MX_LENGTH)
            cnt_unq = Order.objects.filter(
                unique_reference=self.unique_reference).count()
            if cnt_unq == 0:
                unq = False
            else:
                failed_count += 1

        super(Order, self).save(*args, **kwargs)

    @property
    def payment_deadline(self):
        '''returns datetime of payment_deadline (creation + payment_window)'''
        # TODO: Use this for pay until message on 'order success' screen
        return (self.created_on + timedelta(minutes=self.payment_window))

    @property
    def expired(self):
        '''Is expired if payment_deadline is exceeded and it's not paid yet'''
        # TODO: validate this business rule
        return (timezone.now() > self.payment_deadline) and (not self.is_paid)

    @property
    def frozen(self):
        '''return a boolean indicating if order can be updated
        Order is frozen if it is expired or has been paid
        '''
        # TODO: validate this business rule
        return self.expired or self.is_paid

    @property
    def has_withdraw_address(self):
        '''return a boolean indicating if order has a withdraw adrress defined
        '''
        # TODO: Validate this buisness rule
        return self.transaction_set.all().count() > 0


class Payment(TimeStampedModel, SoftDeletableModel):
    amount_cash = models.FloatField()
    currency = models.ForeignKey(Currency)
    is_redeemed = models.BooleanField(default = False)
    unique_reference = models.CharField(max_length=UNIQUE_REFERENCE_LENGTH)
    # Super admin if we are paying for BTC
    user = models.ForeignKey(User)
    # Todo consider one to many for split payments, consider order field on
    # payment
    order = models.ForeignKey(Order, null=True)

    def save(self, *args, **kwargs):
        unq = True
        failed_count = 0
        MX_LENGTH = UNIQUE_REFERENCE_LENGTH
        while unq:

            if failed_count >= REFERENCE_LOOKUP_ATTEMPS:
                MX_LENGTH += 1

            self.unique_reference = get_random_string(
                length=MX_LENGTH)
            cnt_unq = Order.objects.filter(
                unique_reference=self.unique_reference).count()
            if cnt_unq == 0:
                unq = False
            else:
                failed_count += 1

        super(Payment, self).save(*args, **kwargs)

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
    address = models.CharField(max_length=35, validators=[validate_bc])
    user = models.ForeignKey(User)


class Transaction(BtcBase):
    # null if withdraw from our balance on Kraken
    address_from = models.ForeignKey(Address, related_name='address_from')
    address_to = models.ForeignKey(Address, related_name='address_to')
    order = models.ForeignKey(Order)
    is_verified = models.BooleanField(default=False)


class PaymentMethod(TimeStampedModel, SoftDeletableModel):
    name = models.CharField(max_length=100)
    handler = models.CharField(max_length=100, null=True)
    fee = models.FloatField(null=True)


class PaymentPreference(TimeStampedModel, SoftDeletableModel):
    # NULL or Admin for out own (buy adds)
    user = models.ForeignKey(User)
    payment_method = models.ForeignKey(PaymentMethod)
    # Optional, sometimes we need this to confirm
    method_owner = models.CharField(max_length=100)
    identified = models.CharField(max_length=100)
    comment = models.CharField(max_length=255)
