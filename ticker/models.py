from django.db import models
from django.utils.dateformat import format
from core.models import Pair

from core.common.models import IndexTimeStampedModel


class Ticker(IndexTimeStampedModel):
    ask = models.DecimalField(max_digits=18, decimal_places=8)
    bid = models.DecimalField(max_digits=18, decimal_places=8)
    pair = models.ForeignKey(Pair)

    @property
    def rate(self):
        return (self.ask + self.bid) / 2


class Price(IndexTimeStampedModel):

    ticker = models.ForeignKey(Ticker, blank=True, null=True)
    pair = models.ForeignKey(Pair, blank=True, null=True)
    better_adds_count = models.IntegerField(default=0)

    @property
    def unix_time(self):
        return format(self.created_on, 'U')

    @property
    def price_formatted_ask(self):
        return self.ticker.ask

    @property
    def price_formatted_bid(self):
        return self.ticker.bid

    def __str__(self):
        return '{} {}'.format(self.pair, self.created_on)
