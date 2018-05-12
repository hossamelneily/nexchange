from core.common.models import TimeStampedModel
from core.validators import validate_eth
from orders.models import Order
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Subscription(TimeStampedModel):
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

    @property
    def users_emails(self):
        return [user.email for user in self.users.all()]

    def __str__(self):
        return "{} {}".format(self.email, self.sending_address)
