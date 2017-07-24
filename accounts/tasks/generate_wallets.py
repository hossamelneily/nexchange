from __future__ import absolute_import
from django.conf import settings
from nexchange.api_clients.factory import ApiClientFactory
from core.models import AddressReserve
from core.models import Currency
from nexchange.utils import get_nexchange_logger


def renew_cards_reserve(expected_reserve=settings.CARDS_RESERVE_COUNT):
    logger = get_nexchange_logger(__name__)
    if settings.DEBUG:
        logger.info(
            expected_reserve,
            settings.API1_USER,
            settings.API1_PASS
        )

    currencies = Currency.objects.filter(is_crypto=True, disabled=False)

    for curr in currencies:
        api = ApiClientFactory.get_api_client(curr.wallet)
        count = AddressReserve.objects\
            .filter(user=None, currency=curr, disabled=False).count()
        while count < expected_reserve:
            address_res = api.create_address(curr)
            AddressReserve.objects.get_or_create(**address_res)
            logger.info(
                "new card currency: {}, address: {}".format(
                    curr.code, address_res['address']))

            count = AddressReserve.objects\
                .filter(user=None, currency=curr, disabled=False).count()
