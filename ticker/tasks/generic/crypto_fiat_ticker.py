from decimal import Decimal
import requests
import requests_cache

from ticker.models import Price
from ticker.tasks.generic.base import BaseTicker
from django.conf import settings


requests_cache.install_cache('btc_crypto_cache',
                             expire_after=settings.TICKER_INTERVAL,
                             backend=settings.TICKER_CACHE_BACKEND)


class CryptoFiatTicker(BaseTicker):
    def get_ticker_crypto_fiat(self):
        price = self.handle()
        prices = self.convert_fiat(price)
        self.get_base_multiplier()
        if prices:
            ticker = self.create_ticker(
                prices['ask'], prices['bid']
            )
            price = Price(pair=self.pair, ticker=ticker, market=self.market)
            return ticker, price

    def convert_fiat(self, price):
        code = self.pair.quote.code
        prices = {}
        nested_ask = price.get('ask', {})
        nested_bid = price.get('bid', {})
        price_rub_ask = nested_ask.get('price_rub', 0)
        price_rub_bid = nested_bid.get('price_rub', 0)
        price_usd_ask = nested_ask.get('price_usd', 0)
        price_usd_bid = nested_bid.get('price_usd', 0)
        if all([code == 'RUB', price_rub_ask, price_rub_bid]):
            prices.update({
                'ask': price_rub_ask,
                'bid': price_rub_bid
            })
        elif code == 'USD':
            prices.update({
                'ask': price_usd_ask,
                'bid': price_usd_bid
            })
        else:
            fixer_info = self.get_fixer_info()
            price_ask = self.usd_to_fiat(code, price_usd_ask, fixer_info)
            price_bid = self.usd_to_fiat(code, price_usd_bid, fixer_info)
            prices.update({
                'ask': price_ask,
                'bid': price_bid
            })
        return prices

    def get_fixer_info(self):
        rate_info = requests.get(self.FIAT_RATE_RESOURCE).json()
        return rate_info

    def usd_to_fiat(self, code, rate_usd, rate_info):
        if code == 'EUR':
            eur_base = Decimal('1.0')
        else:
            eur_base = Decimal(rate_info['rates'][code])
        rate = rate_usd * eur_base / Decimal(rate_info['rates']['USD'])
        return rate
