from celery import shared_task

from django.conf import settings

from core.models import Pair
from ticker.tasks.generic.crypto_fiat_ticker import \
    CryptoFiatKrakenTicker, CryptoFiatCryptopiaTicker, \
    CryptoFiatCoinexchangeTicker, CryptoFiatBittrexTicker,\
    CryptoFiatBitgrailTicker
from ticker.tasks.generic.crypto_crypto_ticker import \
    CryptoCryptoKrakenTicker, CryptoCryptoCryptopiaTicker, \
    CryptoCryptoCoinexchangeTicker, CryptoCryptoBittrexTicker,\
    CryptoCryptoBitgrailTicker
from nexchange.utils import get_nexchange_logger


crypto_fiat_ticker_kraken = CryptoFiatKrakenTicker()
crypto_fiat_ticker_cryptopia = CryptoFiatCryptopiaTicker()
crypto_fiat_ticker_coinexchange = CryptoFiatCoinexchangeTicker()
crypto_fiat_ticker_bittrex = CryptoFiatBittrexTicker()
crypto_fiat_ticker_bitgrail = CryptoFiatBitgrailTicker()
crypto_crypto_ticker_kraken = CryptoCryptoKrakenTicker()
crypto_crypto_ticker_cryptopia = CryptoCryptoCryptopiaTicker()
crypto_crypto_ticker_coinexchange = CryptoCryptoCoinexchangeTicker()
crypto_crypto_ticker_bittrex = CryptoCryptoBittrexTicker()
crypto_crypto_ticker_bitgrail = CryptoCryptoBitgrailTicker()


def get_ticker_crypto_fiat(**kwargs):
    pair_pk = kwargs.get('pair_pk', None)
    logger = get_nexchange_logger(__name__, True, True)
    if pair_pk:
        pair = Pair.objects.get(pk=pair_pk)
        if pair.base.ticker == 'kraken':
            ticker_api = crypto_fiat_ticker_kraken
        elif pair.base.ticker == 'cryptopia':
            ticker_api = crypto_fiat_ticker_cryptopia
        elif pair.base.ticker == 'coinexchange':
            ticker_api = crypto_fiat_ticker_coinexchange
        elif pair.base.ticker == 'bittrex':
            ticker_api = crypto_fiat_ticker_bittrex
        elif pair.base.ticker == 'bitgrail':
            ticker_api = crypto_fiat_ticker_bitgrail
        else:
            ticker_api = None
            logger.error('pair {} no ticker defined'.format(pair))
        ticker_api.run(pair_pk)
        if pair.name in settings.LOCALBTC_PAIRS:
            ticker_api.run(pair_pk, market_code='locbit')
    else:
        logger.warning('pair_pk is not defined in kwargs')


def get_ticker_crypto_crypto(**kwargs):
    logger = get_nexchange_logger(__name__, True, True)
    pair_pk = kwargs.get('pair_pk', None)
    if pair_pk:
        pair = Pair.objects.get(pk=pair_pk)
        if pair.quote.ticker == 'kraken':
            return crypto_crypto_ticker_kraken.run(pair_pk)
        elif pair.quote.ticker == 'cryptopia':
            return crypto_crypto_ticker_cryptopia.run(pair_pk)
        elif pair.quote.ticker == 'coinexchange':
            return crypto_crypto_ticker_coinexchange.run(pair_pk)
        elif pair.quote.ticker == 'bittrex':
            return crypto_crypto_ticker_bittrex.run(pair_pk)
        elif pair.quote.ticker == 'bitgrail':
            return crypto_crypto_ticker_bitgrail.run(pair_pk)
        else:
            logger.error('pair {} no ticker defined'.format(pair))
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
