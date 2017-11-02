from django.conf import settings
from .base import BaseApiClient
from decimal import Decimal
from core.models import Currency, Address
import requests
from time import time
import urllib
import json
import hmac
import hashlib
import base64


class PublicCryptopia:
    BASE_URL = 'https://www.cryptopia.co.nz/api/'

    def get_currencies(self):
        return requests.get(self.BASE_URL + 'GetCurrencies').json()

    def get_trade_pairs(self):
        return requests.get(self.BASE_URL + 'GetTradePairs').json()

    def get_markets(self):
        return requests.get(self.BASE_URL + 'GetMarkets').json()

    def _get_market_endpoint(self, endpoint, trade_pair_id=None,
                             market_name=None, hours=None):
        endpoint += '/{}'
        if trade_pair_id:
            endpoint = endpoint.format(trade_pair_id)
        elif market_name:
            endpoint = endpoint.format(market_name)
        if hours:
            endpoint += '/{}'.format(hours)
        return requests.get(self.BASE_URL + endpoint).json()

    def get_market(self, trade_pair_id=None, market_name=None, hours=None):
        return self._get_market_endpoint(
            'GetMarket', trade_pair_id=trade_pair_id, market_name=market_name,
            hours=hours
        )


class Cryptopia(PublicCryptopia):

    def __init__(self, key=None, secret=None):
        self.key = key
        self.secret = secret

    def get_private_headers(self, url, post_data):
        nonce = str(time())
        md5 = hashlib.md5()
        md5.update(post_data.encode('utf-8'))
        rcb64 = base64.b64encode(md5.digest())
        signature = \
            self.key + "POST" + urllib.parse.quote_plus(url).lower() \
            + nonce + rcb64.decode('utf-8')
        sign = base64.b64encode(
            hmac.new(bytes(self.secret, 'utf-8'),
                     signature.encode('utf-8'), hashlib.sha256).digest()
        )
        header_value = \
            "amx " + self.key + ":" + sign.decode('utf-8') + ":" + nonce
        return {'Authorization': header_value,
                'Content-Type': 'application/json; charset=utf-8'}

    def get_balance(self, currency):
        url = self.BASE_URL + 'GetBalance'
        data = {'Currency': currency}
        post_data = json.dumps(data)
        headers = self.get_private_headers(url, post_data)
        return requests.post(url, data=data, headers=headers)

    def get_deposit_address(self, currency):
        url = self.BASE_URL + 'GetDepositAddress'
        data = {'Currency': currency}
        post_data = json.dumps(data)
        headers = self.get_private_headers(url, post_data)
        return requests.post(url, data=data, headers=headers)


class CryptopiaApiClient(BaseApiClient):

    PAIR_NAME_TEMPLATE = '{base}_{quote}'

    def __init__(self):
        super(CryptopiaApiClient, self).__init__()
        self.api = self.get_api()

    def get_api(self):
        if not self.api:
            self.api = Cryptopia(settings.API5_KEY, settings.API5_SECRET)
        return self.api

    def get_balance(self, currency):
        return Decimal(str(self.get_balance(currency.code)))

    def get_ticker(self, pair):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code,
        )
        return self.api.get_market(market_name=market)

    def get_rate(self, pair, rate_type='Ask'):
        ticker = self.get_ticker(pair)
        rate = ticker.get('Data', {}).get('{}Price'.format(rate_type))
        return Decimal(str(rate))

    def buy_limit(self, pair, amount, rate=None):
        return
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code,
        )
        if not rate:
            rate = float(self.get_rate(pair))
        return self.api.buy(market, rate, amount)

    def sell_limit(self, pair, amount, rate=None):
        return
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code,
        )
        if not rate:
            rate = float(self.get_rate(pair))
        return self.api.sell(market, rate, amount)

    def release_coins(self, currency, address, amount):
        return
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
