from .base import BaseTradeApiClient
from bittrex.bittrex import Bittrex
from django.conf import settings
from decimal import Decimal
from core.models import Address, Currency


class BittrexApiClient(BaseTradeApiClient):

    PAIR_NAME_TEMPLATE = '{quote}-{base}'

    def __init__(self):
        super(BittrexApiClient, self).__init__()
        self.related_nodes = ['api3']
        self.api = self.get_api()

    def get_api(self):
        if not self.api:
            self.api = Bittrex(settings.API3_KEY, settings.API3_SECRET)
        return self.api

    def get_balance(self, currency):
        raw_res = self.api.get_balance(currency.code)
        result = raw_res.get('result', {})
        res = {
            key.lower(): Decimal(str(value))
            for key, value in result.items() if key in ['Pending', 'Balance',
                                                        'Available']
        }
        return res

    def get_ticker(self, pair):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code
        )
        res = self.api.get_ticker(market)
        return res

    def get_rate(self, pair, rate_type='Ask'):
        ticker = self.get_ticker(pair)
        rate = ticker.get('result', {}).get(rate_type, 0)
        return Decimal(str(rate))

    def buy_limit(self, pair, amount, rate=None):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code
        )
        if not rate:
            rate = self.get_rate(pair, rate_type='Ask')
        res = self.api.buy_limit(market, amount, rate)
        return res

    def sell_limit(self, pair, amount, rate=None):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code
        )
        if not rate:
            rate = self.get_rate(pair, rate_type='Bid')
        res = self.api.sell_limit(market, amount, rate)
        return res

    def release_coins(self, currency, address, amount):
        tx_id = None
        if isinstance(currency, Currency):
            currency = currency.code
        if isinstance(address, Address):
            address = address.address
        res = self.api.withdraw(currency, amount, address)
        self.logger.info('Response from Bittrex withdraw: {}'.format(res))
        success = res.get('success', False)
        if success:
            tx_id = res.get('result', {}).get('uuid')
        return tx_id, success
