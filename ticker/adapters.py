import requests
from ticker.fixtures.available_kraken_pairs import kraken_pairs


class BaseApiAdapter:
    def get_quote(self, crypto_pair):
        raise NotImplementedError


class KrakenAdapter(BaseApiAdapter):
    RESOURCE = 'https://api.kraken.com/0/public/Ticker'
    RESOURCE_MARKET = RESOURCE + '?pair={}'

    def __init__(self):
        super(KrakenAdapter, self).__init__()
        self.reverse_pair = True

    @staticmethod
    def kraken_format(code, is_crypto):
        if code == 'DOGE':
            code = 'XDG'
        if code == 'BTC':
            code = 'XBT'
        if is_crypto:
            res = 'X{}'.format(code)
        else:
            res = 'Z{}'.format(code)
        return res

    def pair_api_repr(self, pair):
        quote = self.kraken_format(pair.quote.code, pair.quote.is_crypto)
        base = self.kraken_format(pair.base.code, pair.base.is_crypto)
        reverse_name = '{}{}'.format(quote, base)
        name = '{}{}'.format(base, quote)
        if name in kraken_pairs:
            self.reverse_pair = False
            return name
        elif reverse_name in kraken_pairs:
            self.reverse_pair = True
            return reverse_name
        else:
            raise ValueError(
                'Kraken does not have nor pair {} neither its '
                'reverse pair {}'.format(name, reverse_name)
            )

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
            'reverse': self.reverse_pair,
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
        self.reverse_pair = True
        reverse_pair_name = '{}/{}'.format(
            pair.base.code.upper(),
            pair.quote.code.upper(),
        )
        try:
            desired_market = [market for market in markets
                              if market['Label'] == pair_name].pop()
        except IndexError:
            desired_market = [market for market in markets
                              if market['Label'] == reverse_pair_name].pop()
            self.reverse_pair = False

        res = requests.get(
            self.RESOURCE_TICKER_PARAM.format(desired_market['TradePairId'])
        ).json()['Data']

        return {
            'reverse': self.reverse_pair,
            'ask': res['AskPrice'],
            'bid': res['BidPrice'],
        }


class CoinexchangeAdapter(BaseApiAdapter):
    BASE = 'https://www.coinexchange.io/api/v1/'
    RESOURCE_MARKETS = BASE + 'getmarkets'
    RESOURCE_TICKER_PARAM = BASE + 'getmarketsummary?market_id={}'

    def _get_all_markets(self):
        resp = requests.get(self.RESOURCE_MARKETS)
        return resp

    def get_all_markets(self):
        resp = self._get_all_markets().json().get('result', [])
        return resp

    def get_markets_ids(self, pair):
        res = []
        if not pair.is_crypto:
            return res
        markets = self.get_all_markets()
        for market in markets:
            base = market.get('BaseCurrencyCode', None)
            asset = market.get('MarketAssetCode', None)
            if pair.base.code == base and pair.quote.code == asset:
                res.append(market['MarketID'])
        return res

    def _get_ticker(self, market_id):
        resp = requests.get(self.RESOURCE_TICKER_PARAM.format(market_id))
        return resp

    def get_ticker(self, market_id):
        res = {}
        resp = self._get_ticker(market_id).json()
        all_info = resp.get('result', None)
        message = resp.get(
            'message',
            'Cannot get market(market_id={}) ticker.'.format(market_id))
        if all_info is None:
            res.update({'error': message})
            return res
        ask = all_info.get('AskPrice', None)
        bid = all_info.get('BidPrice', None)
        if ask is None or bid is None:
            return res
        res.update({
            'ask': ask,
            'bid': bid
        })
        return res

    def get_quote(self, pair):
        market_ids = self.get_markets_ids(pair)
        if len(market_ids) == 0:
            return {'error': 'Market {} not found.'.format(pair.name)}
        if len(market_ids) > 1:
            return {'error': 'More than one market for {}.'.format(pair.name)}
        res = self.get_ticker(market_ids[0])
        return res
