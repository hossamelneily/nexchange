from celery import shared_task

from django.conf import settings

from core.models import Pair
from ticker.tasks.generic.btc_fiat_ticker import BtcFiatTicker
from ticker.tasks.generic.btc_crypto_ticker import BtcCryptoTicker
from nexchange.utils import get_nexchange_logger


@shared_task()
def get_ticker_btc_fiat(**kwargs):
    pair = kwargs.get('pair_pk', None)
    logger = get_nexchange_logger(__name__, True, True)
    if pair:
        instance = BtcFiatTicker(pair)
        return instance.run()
    else:
        logger.warning('pair_pk is not defined in kwargs')


@shared_task()
def get_ticker_btc_crypto(**kwargs):
    logger = get_nexchange_logger(__name__, True, True)
    pair_pk = kwargs.get('pair_pk', None)
    if pair_pk:
        instance = BtcCryptoTicker(pair_pk)
        return instance.run()
    else:
        logger.warning('pair_pk is not defined in kwargs')


@shared_task(time_limit=settings.TASKS_TIME_LIMIT)
def get_all_tickers():
    pairs = Pair.objects.filter(disabled=False)
    for pair in pairs:
        kwargs = {'pair_pk': pair.pk}
        if pair.is_crypto:
            get_ticker_btc_crypto.apply(kwargs=kwargs)
        else:
            get_ticker_btc_fiat.apply(kwargs=kwargs)
