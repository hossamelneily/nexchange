from django.db import models
from core.models import TimeStampedModel


class Price(TimeStampedModel):
    BUY = 'B'
    SELL = 'S'
    BUY_SELL_CHOICES = (
        (BUY, 'BUY'),
        (SELL, 'SELL')
    )
    type = models.CharField(max_length=1, choices=BUY_SELL_CHOICES)
    price_rub = models.FloatField()
    price_usd = models.FloatField()
    rate = models.FloatField()
    better_adds_count = models.IntegerField()
