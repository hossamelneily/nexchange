from decimal import Decimal

from core.models import Pair
from ticker.models import Price
from ticker.tasks.generic.base import BaseTicker


class CryptoCryptoTicker(BaseTicker):

    def __init__(self):
        super(CryptoCryptoTicker, self).__init__()
        self.native_ticker = False

    def _get_ticker_crypto(self, pair=None):
        if pair is None:
            pair = self.pair
        base = 'ETH' if any([
            'idex' in pair.quote.ticker.split('/'),
            'idex' in pair.base.ticker.split('/')
        ]) else 'BTC'
        self.native_ticker = any([
            pair.base.code == base,
            pair.quote.code == base
        ])
        if not self.native_ticker:
            if any(['idex' not in self.pair.base.ticker.split('/'),
                    self.pair.quote.code == 'BTC']):
                available_pair = Pair.objects.get(
                    name='{}{}'.format(base, pair.quote.code)
                )
                _ticker = self.get_right_ticker(available_pair)
            else:
                btceth = Pair.objects.get(name='BTCETH')
                btceth_ticker = self.get_right_ticker(btceth)
                eth_ask = Decimal(btceth_ticker.get('ask'))
                eth_bid = Decimal(btceth_ticker.get('bid'))
                btccrypto = Pair.objects.get(
                    name='BTC{}'.format(self.pair.quote.code)
                )
                btccrypto_ticker = self.get_right_ticker(btccrypto)
                btc_ask = Decimal(btccrypto_ticker.get('ask'))
                btc_bid = Decimal(btccrypto_ticker.get('bid'))
                ask = btc_ask / eth_bid
                bid = btc_bid / eth_ask
                _ticker = {'ask': ask, 'bid': bid}
            self.get_base_multiplier(base=base)
        else:
            _ticker = self.get_right_ticker(pair)
        return _ticker

    def get_ticker_crypto(self):
        _ticker = self._get_ticker_crypto()
        ask_quote = _ticker['ask']
        bid_quote = _ticker['bid']
        ticker = self.create_ticker(ask_quote, bid_quote, reverse=False)
        price = Price(pair=self.pair, ticker=ticker, market=self.market)
        return ticker, price

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
