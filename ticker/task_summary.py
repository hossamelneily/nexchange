from celery import shared_task

from django.conf import settings

from core.models import Pair
from ticker.tasks.generic.crypto_fiat_ticker import CryptoFiatTicker
from ticker.tasks.generic.crypto_crypto_ticker import CryptoCryptoTicker
from nexchange.utils import get_nexchange_logger


crypto_fiat_ticker = CryptoFiatTicker()
crypto_crypto_ticker = CryptoCryptoTicker()


@shared_task()
def get_ticker_crypto_fiat(**kwargs):
    pair_pk = kwargs.get('pair_pk', None)
    logger = get_nexchange_logger(__name__, True, True)
    if pair_pk:
        return crypto_fiat_ticker.run(pair_pk)
    else:
        logger.warning('pair_pk is not defined in kwargs')


@shared_task()
def get_ticker_crypto_crypto(**kwargs):
    logger = get_nexchange_logger(__name__, True, True)
    pair_pk = kwargs.get('pair_pk', None)
    if pair_pk:
        return crypto_crypto_ticker.run(pair_pk)
    else:
        logger.warning('pair_pk is not defined in kwargs')


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def get_all_tickers():
    pairs = Pair.objects.filter(disabled=False)
    for pair in pairs:
        kwargs = {'pair_pk': pair.pk}
        if pair.is_crypto:
            get_ticker_crypto_crypto.apply_async(kwargs=kwargs)
        else:
            get_ticker_crypto_fiat.apply_async(kwargs=kwargs)
