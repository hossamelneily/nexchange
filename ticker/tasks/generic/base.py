from decimal import Decimal
import requests
import requests_cache

from core.models import Pair
from ticker.models import Ticker
from nexchange.tasks.base import BaseTask
from django.conf import settings

requests_cache.install_cache('ticker_cache',
                             expire_after=settings.TICKER_INTERVAL,
                             backend=settings.TICKER_CACHE_BACKEND)


class BaseTicker(BaseTask):

    KRAKEN_RESOURCE = 'https://api.kraken.com/0/public/Ticker'

    EUR_RESOURCE = 'http://api.fixer.io/latest'

    BITFINEX_TICKER = "https://api.bitfinex.com/v1/pubticker/btcusd"
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

    def __init__(self, pair_pk):
        super(BaseTicker, self).__init__()
        self.pair = Pair.objects.get(pk=pair_pk)

    def run(self):
        if self.pair.is_crypto:
            price = self.get_ticker_crypto()
        else:
            price = self.get_ticker_crypto_fiat()
        self.logger.info('Price {} created'.format(price))

    def create_ticker(self, ask, bid):
        ask = Decimal(ask) * (Decimal('1.0') + self.pair.fee_ask)
        bid = Decimal(bid) * (Decimal('1.0') - self.pair.fee_bid)
        ticker = Ticker(pair=self.pair, ask=ask,
                        bid=bid)
        ticker.save()
        return ticker

    def handle(self):
        spot_data = requests.get(self.BITFINEX_TICKER).json()
        sell_spot_price = Decimal(spot_data.get('ask', 0))
        sell_price = self.get_price(sell_spot_price, self.ACTION_BUY)
        buy_spot_price = Decimal(spot_data.get('bid', 0))
        buy_price = self.get_price(buy_spot_price, self.ACTION_SELL)
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
