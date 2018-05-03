from django.db import models
from django.utils.dateformat import format
from django.conf import settings
from cached_property import cached_property_with_ttl
from core.models import Pair, Market, Currency

from core.common.models import IndexTimeStampedModel
from decimal import Decimal
from payments.utils import money_format
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from nexchange.utils import get_nexchange_logger

LOGGER = get_nexchange_logger('Ticker Logger', with_email=True,
                              with_console=True)


class Ticker(IndexTimeStampedModel):
    ask = models.DecimalField(max_digits=18, decimal_places=8)
    bid = models.DecimalField(max_digits=18, decimal_places=8)
    pair = models.ForeignKey(Pair)

    @property
    def rate(self):
        return (self.ask + self.bid) / 2

    def _validate(self):
        if self.pk:
            return
        try:
            latest = Ticker.objects.filter(pair=self.pair).latest('id')
        except self.DoesNotExist:
            return
        for field in ['ask', 'bid']:
            value = Decimal(getattr(self, field))
            previous_value = Decimal(getattr(latest, field))
            diff = abs(value - previous_value) / previous_value
            if diff > settings.TICKER_ALLOWED_CHANGE:
                msg = \
                    'Too big ticker {field} change (from {value} to ' \
                    '{previous_value}). Pair: {pair}'.format(
                        field=field,
                        value=value,
                        previous_value=previous_value,
                        pair=self.pair.name
                    )
                LOGGER.info(msg)
                raise ValidationError(_(msg))

    def save(self, *args, **kwargs):
        self._validate()
        super(Ticker, self).save(*args, **kwargs)


DEFAULT_MARKET_PK = 1


class Price(IndexTimeStampedModel):

    ticker = models.ForeignKey(Ticker, blank=True, null=True)
    pair = models.ForeignKey(Pair, blank=True, null=True)
    better_adds_count = models.IntegerField(default=0)
    market = models.ForeignKey(Market, default=DEFAULT_MARKET_PK)
    slippage = models.DecimalField(max_digits=18, decimal_places=8,
                                   default=Decimal('0'))

    def _validate(self):
        if not self.pk and not self.ticker:
            raise ValidationError(_('Ticker is required for Price.'))

    def save(self, *args, **kwargs):
        self._validate()
        if self.pair:
            self.slippage = self.pair.base.current_slippage
        super(Price, self).save(*args, **kwargs)

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

    @property
    def price_expiration_date(self):
        return self.created_on + settings.TICKER_EXPIRATION_INTERVAL

    @property
    def expired(self):
        return timezone.now() > self.price_expiration_date

    def __str__(self):
        return '{} {}'.format(self.pair, self.created_on)
