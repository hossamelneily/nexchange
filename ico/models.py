from core.common.models import TimeStampedModel
from core.validators import validate_eth
from orders.models import Order
from django.db import models
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
