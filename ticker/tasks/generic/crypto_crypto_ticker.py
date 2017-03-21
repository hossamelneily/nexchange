from decimal import Decimal

from core.models import Pair
from ticker.models import Price
from ticker.tasks.generic.base import BaseTicker


class CryptoCryptoTicker(BaseTicker):

    def get_ticker_crypto(self):
        if self.pair.base.code != 'BTC':
            available_pair = Pair.objects.get(
                name='BTC{}'.format(self.pair.quote.code)
            )
            kraken_pair = available_pair.invert_kraken_style
        else:
            kraken_pair = self.pair.invert_kraken_style
        kraken_ticker = self.get_kraken_ticker(kraken_pair)
        ask_quote = kraken_ticker['ask']
        bid_quote = kraken_ticker['bid']
        self.get_kraken_base_multiplier()
        ticker = self.create_ticker(ask_quote, bid_quote)
        price = Price(pair=self.pair, ticker=ticker)
        price.save()
        return price

    def create_ticker(self, ask_quote, bid_quote):
        """ This method inverts ask, bid of the parents.
        Kraken resource only allows other_crypto/BTC pairs.
        """
        ask_base = Decimal('1.0') / Decimal(bid_quote)
        bid_base = Decimal('1.0') / Decimal(ask_quote)
        return super(CryptoCryptoTicker, self).create_ticker(ask_base, bid_base)

    def get_ticker_crypto_fiat(self):
        price = self.handle()
        prices = self.convert_fiat(price)
        if prices:
            ticker = self.create_ticker(prices['ask'], prices['bid'])
            price = Price(pair=self.pair, ticker=ticker)
            price.save()
