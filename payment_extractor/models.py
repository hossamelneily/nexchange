from django.db import models

from nexchange.core.models import TimeStampedModel, SoftDeletableModel
from django.contrib.auth.models import User
from nexchange.nexchange.settings import UNIQUE_REFERENCE_LENGTH

class Payment(TimeStampedModel, SoftDeletableModel):
    amount_cash = models.FloatField()
    currency = models.ForeignKey(User)
    is_redeemed = models.BooleanField()
    # To match order
    # TODO: export max_length of reference to settings
    unique_reference = models.CharField(max_length=UNIQUE_REFERENCE_LENGTH)