from django.db import models

from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField
from safedelete import safedelete_mixin_factory, SOFT_DELETE, \
    DELETED_VISIBLE_BY_PK, safedelete_manager_factory, DELETED_INVISIBLE

from safedelete import safedelete_mixin_factory, SOFT_DELETE, \
    DELETED_VISIBLE_BY_PK, safedelete_manager_factory, DELETED_INVISIBLE

from nexchange.nexchange.settings import UNIQUE_REFERENCE_LENGTH


class TimeStampedModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


SoftDeleteMixin = safedelete_mixin_factory(policy=SOFT_DELETE,
                                           visibility=DELETED_VISIBLE_BY_PK)

class SoftDeletableModel(SoftDeleteMixin):
    disabled = models.BooleanField(default=False)
    active_objects = safedelete_manager_factory(models.Manager, models.QuerySet,
                                                DELETED_INVISIBLE)()

    class Meta:
        abstract = True


class Profile(TimeStampedModel, SoftDeletableModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = PhoneNumberField(blank=False)
    first_name = models.CharField(max_length=20, blank=True)
    last_name = models.CharField(max_length=20, blank=True)


class Currency(TimeStampedModel, SoftDeletableModel):
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=10)


class Order(TimeStampedModel, SoftDeletableModel):
    amount_cash = models.FloatField()
    amount_btc = models.FloatField()
    currency = models.ForeignKey(Currency)
    payment_window = models.IntegerField()
    rate_usd_btc = models.FloatField()
    rate_usd_rub = models.FloatField()
    user = models.ForeignKey(User)
    is_paid = models.BooleanField(default=False)
    is_released = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    # TODO: export max_length of reference to settings
    unique_reference = models.CharField(max_length=5)
    admin_comment = models.CharField(max_length=200)
    wallet = models.CharField(max_length=32)


    def save(self, *args, **kwargs):
        # TODO: export max_length of reference to settings
        self.unique_reference = get_random_string(length=UNIQUE_REFERENCE_LENGTH)
        super(Order, self).save(*args, **kwargs)

    def rate_btc_rub(self):
        return self.rate_usd_rub * self.rate_usd_btc

class Payment(TimeStampedModel, SoftDeletableModel):
    amount_cash = models.FloatField()
    currency = models.ForeignKey(Currency)
    is_redeemed = models.BooleanField()
    # To match order
    # TODO: export max_length of reference to settings
    unique_reference = models.CharField(max_length=5)
