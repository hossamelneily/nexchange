from decimal import Decimal
import requests

from ticker.models import Price
from ticker.tasks.generic.base import BaseTicker


class BtcCryptoTicker(BaseTicker):

    def get_ticker_crypto(self):
        kraken_pair = self.pair.invert_kraken_style
        info = requests.get(self.KRAKEN_RESOURCE + '?pair={}'.format(
            kraken_pair
        )).json()['result']
        ask_quote = info[kraken_pair]['a'][0]
        bid_quote = info[kraken_pair]['b'][0]
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
        return super(BtcCryptoTicker, self).create_ticker(ask_base, bid_base)

    def get_ticker_crypto_fiat(self):
        price = self.handle()
        prices = self.convert_fiat(price)
        if prices:
            ticker = self.create_ticker(prices['ask'], prices['bid'])
            price = Price(pair=self.pair, ticker=ticker)
            price.save()
