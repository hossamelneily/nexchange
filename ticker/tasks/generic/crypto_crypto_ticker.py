from decimal import Decimal

from core.models import Pair
from ticker.models import Price
from ticker.tasks.generic.base import BaseTicker,\
    KrakenBaseTicker, CryptopiaBaseTicker, CoinexchangeBaseTicker


class CryptoCryptoTicker(BaseTicker):

    def get_ticker_crypto(self):
        if self.pair.base.code != 'BTC' and self.pair.quote.code != 'BTC':
            available_pair = Pair.objects.get(
                name='BTC{}'.format(self.pair.quote.code)
            )
            pair = self.quote_api_adapter.get_quote(available_pair)
        else:
            pair = self.quote_api_adapter.get_quote(self.pair)
        ask_quote = pair['ask']
        bid_quote = pair['bid']
        reverse = pair.get('reverse', True)
        self.get_btc_base_multiplier()
        ticker = self.create_ticker(ask_quote, bid_quote, reverse=reverse)
        price = Price(pair=self.pair, ticker=ticker)
        price.save()
        return price

    def create_ticker(self, ask_quote, bid_quote, reverse=True):
        """ This method inverts ask, bid of the parents.
        Kraken resource only allows other_crypto/BTC pairs.
        """
        if reverse:
            ask_base = Decimal('1.0') / Decimal(bid_quote)
            bid_base = Decimal('1.0') / Decimal(ask_quote)
        else:
            ask_base = ask_quote
            bid_base = bid_quote
        return super(CryptoCryptoTicker, self)\
            .create_ticker(ask_base, bid_base)

    def get_ticker_crypto_fiat(self):
        # todo: why is fiat method in crypto to crypto class?
        price = self.handle()
        prices = self.convert_fiat(price)
        if prices:
            ticker = self.create_ticker(prices['ask'], prices['bid'])
            price = Price(pair=self.pair, ticker=ticker)
            price.save()


class CryptoCryptoKrakenTicker(CryptoCryptoTicker, KrakenBaseTicker):
    pass


class CryptoCryptoCryptopiaTicker(CryptoCryptoTicker, CryptopiaBaseTicker):
    pass


class CryptoCryptoCoinexchangeTicker(CryptoCryptoTicker,
                                     CoinexchangeBaseTicker):
    pass
