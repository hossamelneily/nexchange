from decimal import Decimal

from core.models import Pair
from ticker.models import Price
from ticker.tasks.generic.base import BaseTicker,\
    KrakenBaseTicker, CryptopiaBaseTicker, CoinexchangeBaseTicker,\
    BittrexBaseTicker, BitgrailBaseTicker, IdexBaseTicker, KucoinBaseTicker


class CryptoCryptoTicker(BaseTicker):

    def __init__(self):
        super(CryptoCryptoTicker, self).__init__()
        self.native_ticker = False

    def _get_ticker_crypto(self, pair=None):
        if pair is None:
            pair = self.pair
        base = 'ETH' if any([
            pair.quote.ticker in ['idex'],
            pair.base.ticker in ['idex']
        ]) else 'BTC'
        self.native_ticker = any([
            pair.base.code == base,
            pair.quote.code == base
        ])

        if not self.native_ticker:
            if any([self.pair.base.ticker not in ['idex'],
                    self.pair.quote.code == 'BTC']):
                available_pair = Pair.objects.get(
                    name='{}{}'.format(base, pair.quote.code)
                )
                api_adapter = self.get_api_adapter(available_pair)
                _ticker = api_adapter.get_normalized_quote(available_pair)
            else:
                btceth = Pair.objects.get(name='BTCETH')
                api_adapter = self.get_api_adapter(btceth)
                btceth_ticker = api_adapter.get_normalized_quote(btceth)
                eth_ask = Decimal(btceth_ticker.get('ask'))
                eth_bid = Decimal(btceth_ticker.get('bid'))
                btccrypto = Pair.objects.get(
                    name='BTC{}'.format(self.pair.quote.code)
                )
                api_adapter = self.get_api_adapter(btccrypto)
                btccrypto_ticker = api_adapter.get_normalized_quote(btccrypto)
                btc_ask = Decimal(btccrypto_ticker.get('ask'))
                btc_bid = Decimal(btccrypto_ticker.get('bid'))
                ask = btc_ask / eth_bid
                bid = btc_bid / eth_ask
                _ticker = {'ask': ask, 'bid': bid}
            self.get_base_multiplier(base=base)
        else:
            api_adapter = self.get_api_adapter(pair)
            _ticker = api_adapter.get_normalized_quote(pair)
        return _ticker

    def get_ticker_crypto(self):
        _ticker = self._get_ticker_crypto()
        ask_quote = _ticker['ask']
        bid_quote = _ticker['bid']
        ticker = self.create_ticker(ask_quote, bid_quote, reverse=False)
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


class CryptoCryptoBittrexTicker(CryptoCryptoTicker, BittrexBaseTicker):
    pass


class CryptoCryptoBitgrailTicker(CryptoCryptoTicker, BitgrailBaseTicker):
    pass


class CryptoCryptoIdexTicker(CryptoCryptoTicker, IdexBaseTicker):
    pass


class CryptoCryptoKucoinTicker(CryptoCryptoTicker, KucoinBaseTicker):
    pass
