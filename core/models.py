from django.db import models

from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField
from safedelete import safedelete_mixin_factory, SOFT_DELETE, \
    DELETED_VISIBLE_BY_PK, safedelete_manager_factory, DELETED_INVISIBLE

from safedelete import safedelete_mixin_factory, SOFT_DELETE, \
    DELETED_VISIBLE_BY_PK, safedelete_manager_factory, DELETED_INVISIBLE

from nexchange.settings import UNIQUE_REFERENCE_LENGTH, PAYMENT_WINDOW

import string
import random


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
    phone = PhoneNumberField(blank=False, help_text='Enter phone number in internation format. eg. +555198786543')
    first_name = models.CharField(max_length=20, blank=True)
    last_name = models.CharField(max_length=20, blank=True)
    sms_token = models.CharField(max_length=UNIQUE_REFERENCE_LENGTH, blank=True)

    @staticmethod
    def make_sms_token():
        unq = True
        while unq:
            token = get_random_string(length=UNIQUE_REFERENCE_LENGTH)
            cnt_unq = Profile.objects.filter(sms_token=token).count()
            if cnt_unq == 0:
                unq = False

            return token

    def save(self, *args, **kwargs):
        '''Add a SMS token at creation. It will be used to verify phone number'''
        if self.pk is None:
            self.sms_token = Profile.make_sms_token()
        super(Profile, self).save(*args, **kwargs)

User.profile = property(lambda u: Profile.objects.get_or_create(user=u)[0])



class Currency(TimeStampedModel, SoftDeletableModel):
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Order(TimeStampedModel, SoftDeletableModel):
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
    wallet = models.CharField(max_length=32)

    class Meta:
        ordering = ['-created_on']

    def save(self, *args, **kwargs):
        unq = True
        failed_count = 0
        MX_LENGTH = UNIQUE_REFERENCE_LENGTH
        while unq:     
            
            if failed_count >= 5:
                MX_LENGTH += 1

            self.unique_reference = get_random_string(
                length=MX_LENGTH)
            cnt_unq = Order.objects.filter(
                unique_reference=self.unique_reference).count()
            if cnt_unq == 0:
                unq = False
            else:
                failed_count+=1

        super(Order, self).save(*args, **kwargs)


class Payment(TimeStampedModel, SoftDeletableModel):
    amount_cash = models.FloatField()
    currency = models.ForeignKey(Currency)
    is_redeemed = models.BooleanField()
    # To match order
    # TODO: export max_length of reference to settings
    unique_reference = models.CharField(max_length=5)
