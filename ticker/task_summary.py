from celery import shared_task

from django.conf import settings

from core.models import Pair
from ticker.tasks.generic.crypto_fiat_ticker import \
    CryptoFiatKrakenTicker, CryptoFiatCryptopiaTicker
from ticker.tasks.generic.crypto_crypto_ticker import \
    CryptoCryptoKrakenTicker, CryptoCryptoCryptopiaTicker
from nexchange.utils import get_nexchange_logger
from time import sleep


crypto_fiat_ticker_kraken = CryptoFiatKrakenTicker()
crypto_fiat_ticker_cryptopia = CryptoFiatCryptopiaTicker()
crypto_crypto_ticker_kraken = CryptoCryptoKrakenTicker()
crypto_crypto_ticker_cryptopia = CryptoCryptoCryptopiaTicker()


@shared_task()
def get_ticker_crypto_fiat(**kwargs):
    pair_pk = kwargs.get('pair_pk', None)
    logger = get_nexchange_logger(__name__, True, True)
    if pair_pk:
        pair = Pair.objects.get(pk=pair_pk)
        if pair.base.ticker == 'kraken':
            return crypto_fiat_ticker_kraken.run(pair_pk)
        elif pair.base.ticker == 'cryptopia':
            return crypto_fiat_ticker_cryptopia.run(pair_pk)
        else:
            logger.error('pair {} no ticker defined'.format(pair))
    else:
        logger.warning('pair_pk is not defined in kwargs')


@shared_task()
def get_ticker_crypto_crypto(**kwargs):
    logger = get_nexchange_logger(__name__, True, True)
    pair_pk = kwargs.get('pair_pk', None)
    if pair_pk:
        pair = Pair.objects.get(pk=pair_pk)
        if pair.quote.ticker == 'kraken':
            return crypto_crypto_ticker_kraken.run(pair_pk)
        elif pair.quote.ticker == 'cryptopia':
            return crypto_crypto_ticker_cryptopia.run(pair_pk)
        else:
            logger.error('pair {} no ticker defined'.format(pair))
    else:
        logger.warning('pair_pk is not defined in kwargs')


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def get_all_tickers():
    logger = get_nexchange_logger('Get Tickers')
    pairs = Pair.objects.filter(disabled=False)
    for i, pair in enumerate(pairs):
        if i % 30 == 0:
            # Prevent RDB failures.
            sleep(0.1)
        kwargs = {'pair_pk': pair.pk}
        if pair.is_crypto:
            try:
                get_ticker_crypto_crypto.apply_async(kwargs=kwargs)
            except Exception as e:
                logger.warning(
                    'Smth is wrong with pair:{} ticker. traceback:{}'.format(
                        pair, e)
                )

        else:
            try:
                get_ticker_crypto_fiat.apply_async(kwargs=kwargs)
            except Exception as e:
                logger.warning(
                    'Smth is wrong with pair:{} ticker. traceback:{}'.format(
                        pair, e)
                )
