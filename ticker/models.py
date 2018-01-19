from django.db import models
from django.utils.dateformat import format
from django.conf import settings
from cached_property import cached_property_with_ttl
from core.models import Pair, Market, Currency

from core.common.models import IndexTimeStampedModel
from decimal import Decimal
from payments.utils import money_format


class Ticker(IndexTimeStampedModel):
    ask = models.DecimalField(max_digits=18, decimal_places=8)
    bid = models.DecimalField(max_digits=18, decimal_places=8)
    pair = models.ForeignKey(Pair)

    @property
    def rate(self):
        return (self.ask + self.bid) / 2


DEFAULT_MARKET_PK = 1


class Price(IndexTimeStampedModel):

    ticker = models.ForeignKey(Ticker, blank=True, null=True)
    pair = models.ForeignKey(Pair, blank=True, null=True)
    better_adds_count = models.IntegerField(default=0)
    market = models.ForeignKey(Market, default=DEFAULT_MARKET_PK)
    slippage = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'))

    def save(self):
        if self.pair:
            self.slippage = self.pair.base.current_slippage
        super(Price, self).save()

    @classmethod
    def _get_currency(cls, currency):
        if isinstance(currency, Currency):
            return currency
        return Currency.objects.get(code=currency)

    @classmethod
    def get_rate(cls, base, quote):
        inverted = False
        base = cls._get_currency(base)
        quote = cls._get_currency(quote)
        if base == quote:
            return Decimal('1.0')
        places = 16
        if all([not base.is_crypto, quote.is_crypto]):
            base, quote = quote, base
            inverted = True
            places = 16
        elif all([not base.is_crypto, not quote.is_crypto]):
            places = 16
        try:
            pair = Pair.objects.get(base=base, quote=quote)
            latest_rate = cls.objects.filter(
                pair=pair,
                market__is_main_market=True).latest('id').ticker.rate
            if inverted:
                latest_rate = money_format(Decimal(1.0) / latest_rate,
                                           places=places)
        except Pair.DoesNotExist:
            latest_btc = cls.objects.filter(
                pair__name='BTC{}'.format(quote.code),
                market__is_main_market=True).latest('id').ticker.rate
            latest_base = cls.objects.filter(
                pair__name='BTC{}'.format(base.code),
                market__is_main_market=True).latest('id').ticker.rate
            if inverted:
                latest_rate = money_format(latest_base / latest_btc,
                                           places=places)
            else:
                latest_rate = money_format(latest_btc / latest_base,
                                           places=places)
        return latest_rate

    @classmethod
    def convert_amount(cls, amount, from_curr, to_curr):
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        rate = cls.get_rate(from_curr, to_curr)
        return amount * rate

    @property
    def unix_time(self):
        return format(self.created_on, 'U')

    @property
    def price_formatted_ask(self):
        return self.ticker.ask

    @property
    def price_formatted_bid(self):
        return self.ticker.bid

    @property
    def rate(self):
        return self.ticker.ask * (Decimal('1.0') + self.slippage)

    @cached_property_with_ttl(ttl=settings.TICKER_INTERVAL)
    def rate_btc(self):
        return self.get_rate(self.pair.base, 'BTC')

    @cached_property_with_ttl(ttl=settings.TICKER_INTERVAL)
    def rate_usd(self):
        return self.get_rate(self.pair.base, 'USD')

    @cached_property_with_ttl(ttl=settings.TICKER_INTERVAL)
    def rate_eur(self):
        return self.get_rate(self.pair.base, 'EUR')

    def __str__(self):
        return '{} {}'.format(self.pair, self.created_on)
