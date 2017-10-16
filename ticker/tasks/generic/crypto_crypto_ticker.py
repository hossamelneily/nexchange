from decimal import Decimal

from core.models import Pair
from ticker.models import Price
from ticker.tasks.generic.base import BaseTicker,\
    KrakenBaseTicker, CryptopiaBaseTicker, CoinexchangeBaseTicker


class CryptoCryptoTicker(BaseTicker):

    def __init__(self):
        super(CryptoCryptoTicker, self).__init__()
        self.native_ticker = False

    def get_ticker_crypto(self):
        self.native_ticker = any([
            self.pair.base.code == 'BTC',
            self.pair.quote.code == 'BTC',
            self.pair.name in ['XVGDOGE', 'DOGEXVG']])

        if not self.native_ticker:
            available_pair = Pair.objects.get(
                name='BTC{}'.format(self.pair.quote.code)
            )
            api_adapter = self.get_api_adapter(available_pair)
            pair = api_adapter.get_quote(available_pair)
            self.get_btc_base_multiplier()
        else:
            api_adapter = self.get_api_adapter(self.pair)
            pair = api_adapter.get_quote(self.pair)
        ask_quote = pair['ask']
        bid_quote = pair['bid']
        reverse = pair.get('reverse', True)
        ticker = self.create_ticker(ask_quote, bid_quote, reverse=reverse)
        price = Price(pair=self.pair, ticker=ticker, market=self.market)
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


class CryptoCryptoKrakenTicker(CryptoCryptoTicker, KrakenBaseTicker):
    pass


class CryptoCryptoCryptopiaTicker(CryptoCryptoTicker, CryptopiaBaseTicker):
    pass


class CryptoCryptoCoinexchangeTicker(CryptoCryptoTicker,
                                     CoinexchangeBaseTicker):
    pass
