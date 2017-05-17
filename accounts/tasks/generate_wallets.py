from __future__ import absolute_import
from django.conf import settings
from nexchange.api_clients.factory import ApiClientFactory
from core.models import AddressReserve
from core.models import Currency
from nexchange.utils import get_nexchange_logger, get_traceback


def renew_cards_reserve():
    logger = get_nexchange_logger(__name__)
    logger.info(get_traceback())
    if settings.DEBUG:
        logger.info(
            settings.CARDS_RESERVE_COUNT,
            settings.API1_USER,
            settings.API1_PASS
        )

    currencies = Currency.objects.filter(code__in=['BTC', 'ETH', 'LTC'])

    for curr in currencies:
        api = ApiClientFactory.get_api_client(curr.wallet)
        count = AddressReserve.objects\
            .filter(user=None, currency=curr).count()
        while count < settings.CARDS_RESERVE_COUNT:
            address_res = api.create_address(curr)
            AddressReserve.objects.get_or_create(**address_res)
            logger.info(
                "new card currency: {}, address: {}".format(
                    curr.code, address_res['address']))

            count = AddressReserve.objects\
                .filter(user=None, currency=curr).count()
