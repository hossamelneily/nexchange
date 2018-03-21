from decimal import Decimal
import requests
import requests_cache
import numpy as np

from core.models import Pair, Market
from ticker.models import Ticker
from nexchange.tasks.base import BaseTask
from ticker.adapters import KrakenAdapter, CryptopiaAdapter, \
    CoinexchangeAdapter, BittrexAdapter, BitgrailAdapter, IdexAdapter, \
    KucoinAdapter, BinanceAdapter
from django.conf import settings

requests_cache.install_cache('ticker_cache',
                             expire_after=settings.TICKER_INTERVAL,
                             backend=settings.TICKER_CACHE_BACKEND)

bitgrail_adapter = BitgrailAdapter()
bittrex_adapter = BittrexAdapter()
kraken_adapter = KrakenAdapter()
cryptopia_adapter = CryptopiaAdapter()
coinexchange_adapter = CoinexchangeAdapter()
idex_adapter = IdexAdapter()
kucoin_adapter = KucoinAdapter()
binance_adapter = BinanceAdapter()


class BaseTicker(BaseTask):

    FIAT_RATE_RESOURCE = 'http://api.fixer.io/latest'

    BITFINEX_TICKER = "https://api.bitfinex.com/v1/pubticker/btcusd"
    KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker?pair=XXBTZUSD"
    LOCALBTC_URL =\
        "https://localbitcoins.net/{}-bitcoins-online/" \
        "ru/russian-federation/banks/.json"
    ACTION_SELL = "sell"

    # direction -1
    ACTION_BUY = "buy"

    ALLOWED_CURRENCIES = ["RUB"]
    MIN_TRADE_COUNT = 20
    MIN_FEEDBACK_SCORE = 90
    MIN_INTERVAL = Decimal(0.02)
    DISCOUNT_MULTIPLIER = Decimal(0.001)

    # currently not checked
    MINIMAL_AMOUNT = 10000

    RELEVANT_FIELDS = ['is_low_risk', 'currency', 'temp_price',
                       'temp_price_usd', 'visible',
                       'profile.feedback_score', 'profile.trade_count']

    EXCLUSION_LIST = [
        'GIFT',
        'COUPON',
        'CODE',
        'VOUCHER',
        'EBAY',
        'AMAZON',
        'HOTEL',
        'YANDEX',
        'QIWI',
        'WEBMONEY',
        'PAYPAL',
    ]

    def __init__(self):
        super(BaseTicker, self).__init__()
        self.pair = None
        self.market = None
        self.ask_multip = None
        self.bid_multip = None
        self.quote_api_adapter = None

    def get_api_adapter(self, pair):
        base = 'ETH' if 'idex' in pair.quote.ticker.split('/') else 'BTC'
        currency = pair.quote if pair.base.code == base else pair.base
        adapters = []
        tickers = currency.ticker.split('/')
        for ticker in tickers:
            if ticker == 'kraken':
                adapters.append(kraken_adapter)
            elif ticker == 'cryptopia':
                adapters.append(cryptopia_adapter)
            elif ticker == 'coinexchange':
                adapters.append(coinexchange_adapter)
            elif ticker == 'bittrex':
                adapters.append(bittrex_adapter)
            elif ticker == 'bitgrail':
                adapters.append(bitgrail_adapter)
            elif ticker == 'idex':
                adapters.append(idex_adapter)
            elif ticker == 'kucoin':
                adapters.append(kucoin_adapter)
            elif ticker == 'binance':
                adapters.append(binance_adapter)
            else:
                self.logger.warning('There is no {} adapter'.format(ticker))
        return adapters

    def run(self, pair_pk, market_code='nex'):
        self.market = Market.objects.get(code=market_code)
        self.pair = Pair.objects.get(pk=pair_pk)
        self.ask_multip = self.bid_multip = Decimal('1.0')
        if self.pair.is_crypto:
            return self.get_ticker_crypto()
        else:
            return self.get_ticker_crypto_fiat()

    def create_ticker(self, ask, bid):
        ask = (self.ask_multip * Decimal(ask) *
               (Decimal('1.0') + self.pair.fee_ask))
        bid = (self.bid_multip * Decimal(bid) *
               (Decimal('1.0') - self.pair.fee_bid))
        ticker = Ticker(pair=self.pair, ask=ask,
                        bid=bid)
        return ticker

    def _get_bitfinex_usd_ticker(self):
        res = requests.get(self.KRAKEN_TICKER).json()
        ask = res['result']['XXBTZUSD']['a'][0]
        bid = res['result']['XXBTZUSD']['b'][0]
        return {
            'ask': ask,
            'bid': bid
        }

    def handle(self):
        use_local_btc = self.market.code == 'locbit'
        spot_data = self._get_bitfinex_usd_ticker()
        ask = Decimal(str(spot_data.get('ask')))
        bid = Decimal(str(spot_data.get('bid')))
        if use_local_btc:
            sell_spot_price = bid
            sell_price = self.get_price(sell_spot_price, self.ACTION_BUY)
            buy_spot_price = ask
            buy_price = self.get_price(buy_spot_price, self.ACTION_SELL)
        else:
            sell_price = {
                'price_usd': ask,
            }
            buy_price = {
                'price_usd': bid,
            }

        return {'ask': sell_price, 'bid': buy_price}

    def get_price(self, spot_price, action):
        def filter_exclusions(item):
            if not len(self.EXCLUSION_LIST):
                return True

            if all([excluded not in item['data']['online_provider'].upper() and
                    excluded not in item['data']['bank_name'].upper()
                    for excluded in self.EXCLUSION_LIST]):
                return True
            return False

        def run_filters(res):
            for item in res:
                if all(f(item) for f in [filter_exclusions]):
                    yield item

        url = self.LOCALBTC_URL.format(action)
        data = requests.get(url).json()
        filtered_data = run_filters(data['data']['ad_list'])

        direction = -1 if action == self.ACTION_SELL else 1
        return self.adds_iterator(filtered_data, spot_price, direction)

    def adds_iterator(self, adds, spot_price, direction):
        score_escepe_chars = ['+', ' ']

        def normalize_score(x):
            return int(''.join([char for char in x
                                if char not in score_escepe_chars]))

        rate = None
        rub_price = None
        usd_price = None
        better_adds = -1

        for add in adds:
            add_data = add['data']
            better_adds += 1
            # check correct currency, fixate rate
            if add_data['currency'] in self.ALLOWED_CURRENCIES:
                add_price_rub = Decimal(add_data['temp_price'])
                add_price_usd = Decimal(add_data['temp_price_usd'])
                rate = add_price_rub / add_price_usd
            else:
                continue

            # check boolean flags
            if ('is_low_risk' in add_data and not add_data['is_low_risk'])\
                    or not add_data['visible']:
                continue

            # check user profile
            if int(add_data['profile']['feedback_score']) \
                    < self.MIN_FEEDBACK_SCORE or \
               normalize_score(add_data['profile']['trade_count']) \
                    < self.MIN_TRADE_COUNT:
                continue

            if add_price_usd * direction > spot_price * direction * \
                    (1 + self.MIN_INTERVAL * direction):
                rub_price = add_price_rub * \
                    (1 + direction * self.DISCOUNT_MULTIPLIER)
                usd_price = add_price_usd * \
                    (1 + direction * self.DISCOUNT_MULTIPLIER)
                break

        if rub_price is None or usd_price is None:
            usd_price = spot_price * (1 + self.MIN_INTERVAL)
            rub_price = usd_price * rate

        return {
            'better_adds_count': better_adds,
            'rate_usd': rate,
            'price_usd': usd_price,
            'price_rub': rub_price,
            'type': self.ACTION_BUY if direction < 0 else self.ACTION_SELL
        }

    def get_base_multiplier(self, base=None):
        if base is None:
            base = 'ETH' \
                if 'idex' in self.pair.base.ticker.split('/') \
                else 'BTC'
        ask = bid = Decimal('1.0')
        if self.pair.base.code != base and self.pair.quote.code != base:
            if all(['BTC' in [self.pair.base.code, self.pair.quote.code],
                    base == 'ETH']):
                btceth = Pair.objects.get(name='{}ETH'.format(self.pair.base))
                ticker = self.get_right_ticker(btceth)
                ask = ticker.get('ask')
                bid = ticker.get('bid')
            elif all(['BTC' not in [self.pair.base.code, self.pair.quote.code],
                      base == 'ETH', 'idex' in
                                     self.pair.base.ticker.split('/')]):
                cryptoeth = Pair.objects.get(
                    name='{}ETH'.format(self.pair.base.code)
                )
                cryptoeth_ticker = self.get_right_ticker(cryptoeth)
                eth_ask = Decimal(cryptoeth_ticker.get('ask'))
                eth_bid = Decimal(cryptoeth_ticker.get('bid'))
                btceth = Pair.objects.get(name='BTCETH')
                btceth_ticker = self.get_right_ticker(btceth)
                btc_ask = Decimal(btceth_ticker.get('ask'))
                btc_bid = Decimal(btceth_ticker.get('bid'))
                ask = eth_ask / btc_bid
                bid = eth_bid / btc_ask
            elif all(['BTC' not in [self.pair.base.code, self.pair.quote.code],
                      base == 'ETH', 'idex' not in
                                     self.pair.base.ticker.split('/')]):
                btceth = Pair.objects.get(name='BTCETH')
                btceth_ticker = self.get_right_ticker(btceth)
                eth_ask = Decimal(btceth_ticker.get('ask'))
                eth_bid = Decimal(btceth_ticker.get('bid'))
                btccrypto = Pair.objects.get(
                    name='BTC{}'.format(self.pair.base.code)
                )
                btccrypto_ticker = self.get_right_ticker(btccrypto)
                btc_ask = Decimal(btccrypto_ticker.get('ask'))
                btc_bid = Decimal(btccrypto_ticker.get('bid'))
                ask = eth_ask / btc_bid
                bid = eth_bid / btc_ask
            elif base == 'BTC':
                btccrypto = Pair.objects.get(
                    name='BTC{}'.format(self.pair.base.code)
                )
                btccrypto_ticker = self.get_right_ticker(btccrypto)
                ask = Decimal('1.0') / Decimal(btccrypto_ticker.get('bid'))
                bid = Decimal('1.0') / Decimal(btccrypto_ticker.get('ask'))
            self.ask_multip = ask
            self.bid_multip = bid

    def get_right_ticker(self, pair):
        api_adapters = self.get_api_adapter(pair)
        tickers = self.get_tickers(api_adapters, pair)
        if len(tickers) > 1:
            ticker = get_max_ticker(tickers)
        else:
            ticker = tickers[0]
        return ticker

    def get_tickers(self, api_adapters, pair):
        tickers = []
        for api_adapter in api_adapters:
            quote = api_adapter.get_normalized_quote(pair)
            if quote is not None:
                tickers.append(quote)
            else:
                continue
        return tickers


def get_max_ticker(tickers):
    if isinstance(tickers[0], dict):
        max_ticker = tickers[0]
        for ticker in tickers:
            if max_ticker['ask'] < ticker['ask']:
                max_ticker = ticker
        return max_ticker
    if isinstance(tickers[0], Ticker):
        ticker_ask_array = [ticker.ask for ticker in tickers]
        index = np.argmax(ticker_ask_array)
        ticker = tickers[index]
        return int(index), ticker


def save_ticker_and_price(ticker, price):
    ticker.save()
    price.ticker = ticker
    price.save()
