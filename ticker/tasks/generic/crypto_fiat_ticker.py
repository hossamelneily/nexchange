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
        self.get_kraken_base_multiplier()
        if prices:
            ticker = self.create_ticker(
                prices['ask'], prices['bid']
            )
            price = Price(pair=self.pair, ticker=ticker)
            price.save()
            return price

    def convert_fiat(self, price):
        code = self.pair.quote.code
        prices = {}
        price_rub_ask = price['ask']['price_rub']
        price_rub_bid = price['bid']['price_rub']
        price_usd_ask = price['ask']['price_usd']
        rate_usd_ask = price['ask']['rate_usd']
        price_usd_bid = price['bid']['price_usd']
        rate_usd_bid = price['bid']['rate_usd']
        if code == 'RUB':
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
            rate_ask = self.get_rate(code, rate_usd_ask, fixer_info)
            rate_bid = self.get_rate(code, rate_usd_bid, fixer_info)
            price_ask = Decimal(price_rub_ask / rate_ask)
            price_bid = Decimal(price_rub_bid / rate_bid)
            prices.update({
                'ask': price_ask,
                'bid': price_bid
            })
        return prices

    def get_fixer_info(self):
        rate_info = requests.get(self.EUR_RESOURCE).json()
        return rate_info

    def get_rate(self, code, rate_usd, rate_info):
        if code == 'EUR':
            eur_base = Decimal('1.0')
        else:
            eur_base = Decimal(rate_info['rates'][code])
        rate = Decimal(rate_info['rates']['USD']) * rate_usd / eur_base
        return rate
