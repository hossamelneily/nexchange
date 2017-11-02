from django.conf import settings
from .base import BaseApiClient
from decimal import Decimal
from core.models import Currency, Address
from poloniex import Poloniex


class PoloniexApiClient(BaseApiClient):

    PAIR_NAME_TEMPLATE = '{quote}_{base}'

    def __init__(self):
        super(PoloniexApiClient, self).__init__()
        self.api = self.get_api()

    def get_api(self):
        if not self.api:
            self.api = Poloniex(settings.API4_KEY, settings.API4_SECRET)
        return self.api

    def get_balance(self, currency):
        return Decimal(str(self.api.returnBalances().get(currency.code)))

    def get_ticker(self, pair):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code,
        )
        return self.api.returnTicker().get(market)

    def get_rate(self, pair, **kwargs):
        ticker = self.get_ticker(pair)
        rate = ticker.get('last')
        return Decimal(str(rate))

    def buy_limit(self, pair, amount, rate=None):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code,
        )
        if not rate:
            rate = float(self.get_rate(pair))
        return self.api.buy(market, rate, amount)

    def sell_limit(self, pair, amount, rate=None):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code,
        )
        if not rate:
            rate = float(self.get_rate(pair))
        return self.api.sell(market, rate, amount)

    def release_coins(self, currency, address, amount):
        tx_id = None
        if isinstance(currency, Currency):
            currency = currency.code
        if isinstance(address, Address):
            address = address.address
        res = self.api.withdraw(currency, amount, address)
        self.logger.info('Response from Poloniex withdraw: {}'.format(res))
        success = 'Withdrew' in res.get('response', '')
        if success:
            tx_id = res.get('response')
        return tx_id, success
