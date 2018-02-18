import requests
from ticker.fixtures.available_kraken_pairs import kraken_pairs
from django.core.exceptions import ValidationError
from decimal import Decimal


class BaseApiAdapter:
    def get_quote(self, crypto_pair):
        raise NotImplementedError

    def normalize_quote(self, raw_ticker):
        _ask = Decimal(raw_ticker.get('ask'))
        _bid = Decimal(raw_ticker.get('bid'))
        reverse = raw_ticker.get('reverse')
        assert reverse is not None, 'No reverse parameter defined'
        ask = Decimal('1.0') / _bid if reverse else _ask
        bid = Decimal('1.0') / _ask if reverse else _bid
        return {'ask': ask, 'bid': bid}

    def get_normalized_quote(self, crypto_pair):
        ticker = self.get_quote(crypto_pair)
        return self.normalize_quote(ticker)


class KucoinAdapter(BaseApiAdapter):

    PAIR_NAME_TEMPLATE = '{base}-{quote}'
    BASE_URL = 'https://api.kucoin.com/v1/'

    def __init__(self):
        super(KucoinAdapter, self).__init__()
        self.reverse_pair = False

    def get_markets(self):
        return requests.get(self.BASE_URL + 'open/tick').json()

    def kucoin_format(self, code):
        if code == 'NANO':
            code = 'XRB'
        return code

    def get_quote(self, pair):
        markets = self.get_markets().get('data')
        all_markets = []
        for market in markets:
            all_markets.append(market)
        market_dict = {market['symbol']: market for market in all_markets}
        market = self.PAIR_NAME_TEMPLATE.format(
            base=self.kucoin_format(pair.base.code),
            quote=self.kucoin_format(pair.quote.code)
        )
        reverse_market = self.PAIR_NAME_TEMPLATE.format(
            quote=self.kucoin_format(pair.base.code),
            base=self.kucoin_format(pair.quote.code)
        )
        if market in market_dict:
            self.reverse_pair = False
            result = market_dict[market]
        elif reverse_market in market_dict:
            self.reverse_pair = True
            result = market_dict[reverse_market]
        else:
            raise ValidationError(
                'Ticker and reverse ticker is not available for pair '
                '{}'.format(pair.name)
            )
        ask = result.get('sell')
        bid = result.get('buy')
        return {
            'reverse': self.reverse_pair,
            'ask': ask,
            'bid': bid,
        }


class IdexAdapter(BaseApiAdapter):

    PAIR_NAME_TEMPLATE = '{quote}_{base}'
    BASE_URL = 'https://api.idex.market'

    def __init__(self):
        super(IdexAdapter, self).__init__()
        self.reverse_pair = False

    def get_quote(self, pair):
        if all([pair.quote.code == 'ETH', pair.base.is_token]):
            base = pair.base.code
            quote = pair.quote.code
            self.reverse_pair = False
        elif all([pair.base.code == 'ETH', pair.quote.is_token]):
            base = pair.quote.code
            quote = pair.base.code
            self.reverse_pair = True
        else:
            raise ValidationError(
                'Ticker and reverse ticker is not available for pair '
                '{}'.format(pair.name)
            )

        market = self.PAIR_NAME_TEMPLATE.format(
            base=base,
            quote=quote
        )
        result = requests.post(
            self.BASE_URL + '/returnTicker', json={'market': market}
        ).json()
        ask = bid = result.get('last')
        return {
            'reverse': self.reverse_pair,
            'ask': ask,
            'bid': bid,
        }


class BitgrailAdapter(BaseApiAdapter):

    PAIR_NAME_TEMPLATE = '{base}/{quote}'
    BASE_URL = 'https://api.bitgrail.com/v1/'

    def __init__(self):
        super(BitgrailAdapter, self).__init__()
        self.reverse_pair = False

    def get_markets(self):
        return requests.get(self.BASE_URL + 'markets').json()

    def get_quote(self, pair):
        markets = self.get_markets().get('response')
        all_markets = []
        for market in markets.values():
            all_markets += market
        market_dict = {market['market']: market for market in all_markets}
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code
        )
        reverse_market = self.PAIR_NAME_TEMPLATE.format(
            quote=pair.base.code,
            base=pair.quote.code
        )
        if market in market_dict:
            self.reverse_pair = False
            result = market_dict[market]
        elif reverse_market in market_dict:
            self.reverse_pair = True
            result = market_dict[reverse_market]
        else:
            raise ValidationError(
                'Ticker and reverse ticker is not available for pair '
                '{}'.format(pair.name)
            )
        ask = result.get('ask')
        bid = result.get('bid')
        return {
            'reverse': self.reverse_pair,
            'ask': ask,
            'bid': bid,
        }


class BittrexAdapter(BaseApiAdapter):

    PAIR_NAME_TEMPLATE = '{quote}-{base}'
    BASE_URL = 'https://bittrex.com/api/v1.1/public/'

    def __init__(self):
        super(BittrexAdapter, self).__init__()
        self.reverse_pair = False

    def get_markets(self):
        return requests.get(self.BASE_URL + 'getmarkets').json()

    def check_if_pair_is_available(self, pair):
        markets = self.get_markets()
        result = markets.get('result', {})
        names = [market.get('MarketName') for market in result]
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code
        )
        reverse_market = self.PAIR_NAME_TEMPLATE.format(
            quote=pair.base.code,
            base=pair.quote.code
        )
        pair_available = market in names
        reverse_pair_available = reverse_market in names
        return {'pair_available': pair_available,
                'reverse_pair_available': reverse_pair_available}

    def get_ticker(self, pair, reverse_pair=False):
        market = self.PAIR_NAME_TEMPLATE.format(
            base=pair.base.code,
            quote=pair.quote.code
        )
        if reverse_pair:
            market = self.PAIR_NAME_TEMPLATE.format(
                quote=pair.base.code,
                base=pair.quote.code
            )
        return requests.get(
            self.BASE_URL + 'getticker/?market={}'.format(market)).json()

    def get_quote(self, pair):
        in_result = self.check_if_pair_is_available(pair)
        pair_available = in_result.get('pair_available')
        reverse_pair_available = in_result.get('reverse_pair_available')
        if pair_available:
            self.reverse_pair = False
        elif reverse_pair_available:
            self.reverse_pair = True
        else:
            raise ValidationError(
                'Ticker and reverse ticker is not available for pair '
                '{}'.format(pair.name)
            )
        ticker = self.get_ticker(pair, reverse_pair=self.reverse_pair)
        result = ticker.get('result', {})
        ask = result.get('Ask')
        bid = result.get('Bid')
        return {
            'reverse': self.reverse_pair,
            'ask': ask,
            'bid': bid,
        }


class KrakenAdapter(BaseApiAdapter):
    RESOURCE = 'https://api.kraken.com/0/public/Ticker'
    RESOURCE_MARKET = RESOURCE + '?pair={}'

    def __init__(self):
        super(KrakenAdapter, self).__init__()
        self.reverse_pair = True

    @staticmethod
    def kraken_format(code, is_crypto, add_pad=True):
        if code == 'DOGE':
            code = 'XDG'
        if code == 'BTC':
            code = 'XBT'
        pad = 'X' if is_crypto else 'Z'
        pad = pad if add_pad else ''
        res = '{}{}'.format(pad, code)
        return res

    def pair_api_repr(self, pair):
        add_pad = False if 'EOS' in pair.name else True
        quote = self.kraken_format(pair.quote.code, pair.quote.is_crypto,
                                   add_pad=add_pad)
        base = self.kraken_format(pair.base.code, pair.base.is_crypto,
                                  add_pad=add_pad)
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
        res = requests.get(
            self.RESOURCE_MARKET.format(kraken_pair)
        ).json()['result']

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
            'bid': bid,
            'reverse': True
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
