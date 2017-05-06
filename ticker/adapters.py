import requests


class BaseApiAdapter:
    def get_quote(self, crypto_pair):
        raise NotImplementedError


class KrakenAdapter(BaseApiAdapter):
    RESOURCE = 'https://api.kraken.com/0/public/Ticker'
    RESOURCE_MARKET = RESOURCE + '?pair={}'

    @staticmethod
    def kraken_format(code, is_crypto):
        if code == 'BTC':
            code = 'XBT'
        if is_crypto:
            res = 'X{}'.format(code)
        else:
            res = 'Z{}'.format(code)
        return res

    def pair_api_repr(self, pair):
        base = self.kraken_format(pair.quote.code, pair.quote.is_crypto)
        quote = self.kraken_format(pair.base.code, pair.base.is_crypto)
        return '{}{}'.format(base, quote)

    def get_quote(self, pair):
        """ Available Kraken pairs https://www.kraken.com/help/fees
            @param kraken_pair: currency pair in kranken style
            i.e. BTC and CAD will be XXBTZCAD. Pair model contains kraken_style
            and invert_kraken_style @property's
        """
        kraken_pair = self.pair_api_repr(pair)
        res = requests.get(self.RESOURCE_MARKET.format(
            kraken_pair
        )).json()['result']

        ask = res[kraken_pair]['a'][0]
        bid = res[kraken_pair]['b'][0]
        return {
            'ask': ask,
            'bid': bid,
        }


class CryptopiaAdapter(BaseApiAdapter):
    BASE = 'https://www.cryptopia.co.nz/api/'
    RESOURCE_MARKETS = BASE + 'GetMarkets'
    RESOURCE_TICKER = BASE + 'GetMarket/'
    RESOURCE_TICKER_PARAM = RESOURCE_TICKER + '{}'

    def get_quote(self, pair):
        markets = requests.get(self.RESOURCE_MARKETS).json()['Data']
        pair_name = '{}/{}'.format(
            pair.quote.code.upper(),
            pair.base.code.upper()

        )
        desired_market = [market for market in markets
                          if market['Label'] == pair_name].pop()
        res = requests.get(
            self.RESOURCE_TICKER_PARAM.format(desired_market['TradePairId'])
        ).json()['Data']

        return {
            'ask': res['AskPrice'],
            'bid': res['BidPrice'],
        }
