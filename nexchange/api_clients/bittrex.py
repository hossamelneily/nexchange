from .base import BaseTradeApiClient
from bittrex.bittrex import Bittrex
from django.conf import settings
from decimal import Decimal
from core.models import Address, Currency, Pair


class BittrexApiClient(BaseTradeApiClient):

    PAIR_NAME_TEMPLATE = '{quote}-{base}'

    def __init__(self):
        super(BittrexApiClient, self).__init__()
        self.related_nodes = ['api3']
        self.api = self.get_api()

    def _get_api_currency_code(self, currency_code):
        return currency_code

    def _get_currency_by_api_code(self, api_currency_code):
        return Currency.objects.get(code=api_currency_code)

    def get_api_pairs_for_pair(self, pair):
        reverse_pair = pair.reverse_pair
        markets = self.get_all_active_pairs()
        for _pair in pair, reverse_pair:
            _name = self.get_api_pair_name(_pair)
            if _name in markets:
                return {
                    _pair: {
                        'api_pair_name': _name,
                        'main_currency': self._get_currency_by_api_code(
                            markets[_name]
                        )
                    }
                }
        base_btc = Pair.objects.get(base=pair.base, quote__code='BTC')
        quote_btc = Pair.objects.get(base=pair.quote, quote__code='BTC')
        res = {}
        for _pair in base_btc, quote_btc:
            _name = self.get_api_pair_name(_pair)
            if _name in markets:
                res.update(
                    {_pair: {
                        'api_pair_name': _name,
                        'main_currency': self._get_currency_by_api_code(
                            markets[_name]
                        )
                    }}
                )
        return res

    def get_api_pair_name(self, pair):
        return self.PAIR_NAME_TEMPLATE.format(
            base=self._get_api_currency_code(pair.base.code),
            quote=self._get_api_currency_code(pair.quote.code)
        )

    def get_all_active_pairs(self):
        markets = self.api.get_markets().get('result', [])
        return {
            m.get('MarketName'): m.get('MarketCurrency') for m in markets if m[
                'IsActive'
            ]
        }

    def get_api(self):
        if not self.api:
            self.api = Bittrex(settings.API3_KEY, settings.API3_SECRET)
        return self.api

    def get_balance(self, currency):
        raw_res = self.api.get_balance(self._get_api_currency_code(
            currency.code
        ))
        result = raw_res.get('result', {})
        res = {
            key.lower(): Decimal(str(value if value else 0))
            for key, value in result.items() if key in ['Pending', 'Balance',
                                                        'Available']
        }
        return res

    def get_ticker(self, pair):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=self._get_api_currency_code(pair.base.code),
            quote=self._get_api_currency_code(pair.quote.code)
        )
        res = self.api.get_ticker(market)
        return res

    def get_rate(self, pair, rate_type='Ask'):
        ticker = self.get_ticker(pair)
        rate = ticker.get('result', {}).get(rate_type, 0)
        return Decimal(str(rate))

    def buy_limit(self, pair, amount, rate=None):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=self._get_api_currency_code(pair.base.code),
            quote=self._get_api_currency_code(pair.quote.code)
        )
        if not rate:
            rate = self.get_rate(pair, rate_type='Ask')
        res = self.api.buy_limit(market, amount, rate)
        return res

    def sell_limit(self, pair, amount, rate=None):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=self._get_api_currency_code(pair.base.code),
            quote=self._get_api_currency_code(pair.quote.code)
        )
        if not rate:
            rate = self.get_rate(pair, rate_type='Bid')
        res = self.api.sell_limit(market, amount, rate)
        return res

    def get_main_address(self, currency):
        raw_res = self.api.get_deposit_address(self._get_api_currency_code(
            currency.code
        ))
        result = raw_res.get('result', {})
        address = result.get('Address', None)
        return address if address else None

    def release_coins(self, currency, address, amount):
        tx_id = None
        if isinstance(currency, Currency):
            currency = currency.code
        if isinstance(address, Address):
            address = address.address
        _currency = self._get_api_currency_code(currency)
        res = self.api.withdraw(_currency, amount, address)
        self.logger.info('Response from Bittrex withdraw: {}'.format(res))
        success = res.get('success', False)
        if success:
            tx_id = res.get('result', {}).get('uuid')
        return tx_id, success
