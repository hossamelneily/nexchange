from core.common.models import TimeStampedModel
from core.validators import validate_eth
from orders.models import Order
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils.translation import ugettext as _


class UtmSource(TimeStampedModel):
    name = models.CharField(max_length=255)
    comment = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Subscription(TimeStampedModel):

    LOW = -5
    UNDEFINED = 0
    MEDIUM = 5
    HIGH = 10
    POTENTIAL_TYPES = (
        (UNDEFINED, _('UNDEFINED')),
        (LOW, _('LOW')),
        (MEDIUM, _('MEDIUM')),
        (HIGH, _('HIGH')),
    )
    email = models.EmailField(null=True, blank=True)
    sending_address = models.CharField(max_length=42, null=True,
                                       blank=True, validators=[validate_eth])
    user_comment = models.CharField(max_length=255, null=True, blank=True)
    admin_comment = models.CharField(max_length=255, null=True, blank=True)
    contribution = models.DecimalField(max_digits=18, decimal_places=8,
                                       default=Decimal('0'))
    orders = models.ManyToManyField(Order, null=True, blank=True)
    is_passive = models.BooleanField(default=False)
    users = models.ManyToManyField(User)
    eth_balance = models.DecimalField(max_digits=18, decimal_places=8,
                                      blank=True, null=True,
                                      default=Decimal('0'))
    address_turnover = models.DecimalField(max_digits=18, decimal_places=8,
                                           blank=True, null=True,
                                           default=Decimal('0'),
                                           help_text='Converted to ETH')
    potential = models.IntegerField(
        choices=POTENTIAL_TYPES, default=UNDEFINED
    )
    utm_source = models.ForeignKey(UtmSource, blank=True, null=True)
    category = models.ManyToManyField(Category, null=True, blank=True)

    @property
    def users_emails(self):
        return [user.email for user in self.users.all()]

    @property
    def category_names(self):
        return [cat.name for cat in self.category.all()]

    def __str__(self):
        return "{} {}".format(self.email, self.sending_address)
