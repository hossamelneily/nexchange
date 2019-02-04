from .base import BaseTradeApiClient
import krakenex
from django.conf import settings
from decimal import Decimal
from core.models import Currency, Address
from ticker.adapters import KrakenAdapter


class KrakenApiClient(BaseTradeApiClient, KrakenAdapter):

    def __init__(self):
        KrakenAdapter.__init__(self)
        BaseTradeApiClient.__init__(self)
        self.related_nodes = ['api2']
        self.api = self.get_api()

    def get_api(self):
        if not self.api:
            self.api = krakenex.API()
            self.api.key = settings.API2_KEY
            self.api.secret = settings.API2_SECRET
        return self.api

    def get_balance(self, currency):
        raw_res = self.api.query_private('Balance')
        curr_name = self.kraken_format(currency.code, currency.is_crypto)
        return Decimal(str(raw_res.get('result', {}).get(curr_name)))

    def get_ticker(self, pair):
        market = self.pair_api_repr(pair)
        return self.api.query_public('Ticker', {'pair': market})

    def get_rate(self, pair, rate_type='Ask'):
        ticker = self.get_ticker(pair)
        market = self.pair_api_repr(pair)
        rate = ticker.get('result', {}).get(market, {}).get(
            rate_type[0].lower(), [0])[0]
        return Decimal(str(rate))

    def buy_limit(self, pair, amount, rate=None):
        market = self.pair_api_repr(pair)
        if not rate:
            rate = self.get_rate(pair, rate_type='Ask')
        res = self.api.query_private(
            'AddOrder',
            {'pair': market,
             'type': 'buy',
             'price': '{0:f}'.format(rate),
             'ordertype': 'limit',
             'volume': str(amount)}
        )
        trade_id = res.get('result', {}).get('txid', [None])[0]
        return trade_id, res

    def sell_limit(self, pair, amount, rate=None):
        market = self.pair_api_repr(pair)
        if not rate:
            rate = self.get_rate(pair, rate_type='Bid')
        res = self.api.query_private(
            'AddOrder',
            {'pair': market,
             'type': 'sell',
             'price': '{0:f}'.format(rate),
             'ordertype': 'limit',
             'volume': str(amount)}
        )
        trade_id = res.get('result', {}).get('txid', [None])[0]
        return trade_id, res

    def release_coins(self, currency, address, amount):
        tx_id = None
        if isinstance(currency, Currency):
            is_crypto = currency.is_crypto
            currency = currency.code
        else:
            is_crypto = True
        if isinstance(address, Address):
            address = address.address
        asset = self.kraken_format(currency, is_crypto=is_crypto)
        res = self.api.query_private(
            'Withdraw',
            {'asset': asset, 'key': address, 'amount': str(amount)}
        )
        self.logger.info('Response from Kraken withdraw: {}'.format(res))
        success = not res.get('error', True)
        if success:
            tx_id = res.get('result', {}).get('refid')
        return tx_id, success
