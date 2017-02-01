from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language, ugettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from phonenumber_field.validators import validate_international_phonenumber

from core.common.models import (SoftDeletableModel, TimeStampedModel,
                                UniqueFieldMixin)
from orders.models import Order
from referrals.models import ReferralCode


class NexchangeUser(User):
    username_validator = validate_international_phonenumber

    class Meta:
        proxy = True


class ProfileManager(models.Manager):

    def get_by_natural_key(self, username):
        return self.get(user__username=username)


class Profile(TimeStampedModel, SoftDeletableModel):
    objects = ProfileManager()

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = PhoneNumberField(_('Phone'), blank=False, help_text=_(
        'Enter phone number in international format. eg. +44020786543'))
    first_name = models.CharField(max_length=20, blank=True,
                                  null=True)
    last_name = models.CharField(max_length=20, blank=True,
                                 null=True)
    legal_name = models.CharField(max_length=20, blank=True,
                                  null=True)
    is_company = models.BooleanField(default=False)
    address = models.CharField(max_length=255, default=None,
                               null=True, blank=True)
    last_visit_ip = models.CharField(max_length=39,
                                     default=None, null=True)
    last_visit_time = models.DateTimeField(default=None, null=True)
    notify_by_phone = models.BooleanField(default=True)
    notify_by_email = models.BooleanField(default=True)
    ip = models.CharField(max_length=39,
                          null=True,
                          default=None)
    lang = models.CharField(choices=settings.LANGUAGES,
                            max_length=100,
                            default='en')
    sig_key = models.CharField(max_length=64, blank=True)
    duplicate_of = models.ForeignKey('Profile', blank=True,
                                     null=True, default=None)

    @property
    def partial_phone(self):
        phone = str(self.phone)
        phone_len = len(phone)
        start = phone[:settings.PHONE_START_SHOW - 1]
        end = phone[phone_len - 1 - settings.PHONE_END_SHOW:]
        rest = \
            ''.join([settings.PHONE_HIDE_PLACEHOLDER
                     for x in
                     range(phone_len - settings.PHONE_START_SHOW -
                           settings.PHONE_END_SHOW)])
        return "{}{}{}".format(start, rest, end)

    @property
    def is_banned(self):
        return \
            Order.objects.filter(user=self,
                                 is_paid=True,
                                 expired=True).length \
            > settings.MAX_EXPIRED_ORDERS_LIMIT

    def natural_key(self):
        return self.user.username

    def save(self, *args, **kwargs):
        """Add a SMS token at creation. Used to verify phone number"""
        if self.pk is None:
            token = SmsToken(user=self.user)
            token.save()
        if not self.phone:
            self.phone = self.user.username
        else:
            self.user.username = self.phone
            self.user.save()
        lang = get_language()
        if lang and self.lang != lang:
            self.lang = lang

        # TODO: move to user class, allow many(?)
        ReferralCode.objects.get_or_create(user=self.user)

        return super(Profile, self).save(*args, **kwargs)


# TODO: refactor this Profile is not writable via user
User.profile = property(lambda u:
                        Profile.objects.
                        get_or_create(user=u)[0])


class SmsToken(TimeStampedModel, SoftDeletableModel, UniqueFieldMixin):
    sms_token = models.CharField(
        max_length=settings.SMS_TOKEN_LENGTH, blank=True)
    user = models.ForeignKey(User, related_name='sms_token')

    @staticmethod
    def get_sms_token():
        return User.objects.make_random_password(
            length=settings.SMS_TOKEN_LENGTH,
            allowed_chars=settings.SMS_TOKEN_CHARS
        )

    @property
    def valid(self):
        return self.created_on > timezone.now() -\
            settings.SMS_TOKEN_VALIDITY

    def save(self, *args, **kwargs):
        self.sms_token = self.get_sms_token()
        super(SmsToken, self).save(*args, **kwargs)

    def __str__(self):
        return "{} ({})".format(self.sms_token, self.user.profile.phone)


class Balance(TimeStampedModel):
    user = models.ForeignKey(User, related_name='user')
    currency = models.ForeignKey('core.Currency', related_name='currency')
    balance = models.DecimalField(max_digits=18, decimal_places=8, default=0)
