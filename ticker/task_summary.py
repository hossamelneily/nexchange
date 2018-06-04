from celery import shared_task

from django.conf import settings

from core.models import Pair
from ticker.tasks.generic.base import save_ticker_and_price
from ticker.tasks.generic.crypto_fiat_ticker import CryptoFiatTicker
from ticker.tasks.generic.crypto_crypto_ticker import CryptoCryptoTicker
from nexchange.utils import get_nexchange_logger
from time import time


crypto_fiat_ticker = CryptoFiatTicker()
crypto_crypto_ticker = CryptoCryptoTicker()


def get_ticker_crypto_fiat(**kwargs):
    pair_pk = kwargs.get('pair_pk', None)
    logger = get_nexchange_logger(__name__, True, True)
    if pair_pk:
        pair = Pair.objects.get(pk=pair_pk)
        ticker, price = crypto_fiat_ticker.run(pair_pk)
        save_ticker_and_price(ticker, price)
        if pair.name in settings.LOCALBTC_PAIRS:
            ticker_loc, price_loc = crypto_fiat_ticker.run(
                pair_pk, market_code='locbit'
            )
            save_ticker_and_price(ticker_loc, price_loc, validate_change=False)
    else:
        logger.warning('pair_pk is not defined in kwargs')


def get_ticker_crypto_crypto(**kwargs):
    logger = get_nexchange_logger(__name__, True, True)
    pair_pk = kwargs.get('pair_pk', None)
    if pair_pk:
        ticker, price = crypto_crypto_ticker.run(pair_pk)
        save_ticker_and_price(ticker, price)
    else:
        logger.warning('pair_pk is not defined in kwargs')


@shared_task(time_limit=settings.TASKS_TIME_LIMIT * 2)
def get_all_tickers():
    logger = get_nexchange_logger('Get Tickers')
    pairs = Pair.objects.filter(disable_ticker=False)
    for pair in pairs:
        kwargs = {'pair_pk': pair.pk}
        if pair.is_crypto:
            try:
                get_ticker_crypto_crypto(**kwargs)
            except Exception as e:
                logger.warning(
                    'Smth is wrong with pair:{} ticker. traceback:{}'.format(
                        pair, e)
                )

        else:
            try:
                get_ticker_crypto_fiat(**kwargs)
            except Exception as e:
                logger.warning(
                    'Smth is wrong with pair:{} ticker. traceback:{}'.format(
                        pair, e)
                )
