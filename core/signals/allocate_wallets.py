from core.models import Address, AddressReserve, Currency
from django.db.models.signals import post_save
from django.dispatch import receiver
from nexchange.utils import get_nexchange_logger
from accounts.tasks.generate_wallets import renew_cards_reserve
from django.conf import settings

ALLOWED_SENDERS = ['User', 'NexchangeUser']
logger = get_nexchange_logger('allocate_wallets', True, True)


def create_user_wallet(user, currency):
    unassigned_cards = AddressReserve.objects.filter(currency=currency,
                                                     user=None, disabled=False)
    if len(unassigned_cards) == 0:
        logger.warning('instance {} has no reserve cards available'
                       ' for {} calling renew_cards_reserve()'
                       .format(user, currency))
        renew_cards_reserve(
            expected_reserve=settings.EMERGENCY_CARDS_RESERVE_COUNT)
        unassigned_cards = AddressReserve.objects.filter(currency=currency,
                                                         user=None,
                                                         disabled=False)

    if unassigned_cards:
        # FIFO
        card = unassigned_cards.earliest('id')
        card.user = user
        address = Address(
            address=card.address,
            user=card.user,
            currency=currency,
            type=Address.DEPOSIT,
            reserve=card
        )
        address.save()
        card.save()
        return card, address
    else:
        logger.error('instance {} has no cards available'
                     .format(currency))


@receiver(post_save, dispatch_uid='allocate_wallets')
def allocate_wallets(sender, instance=None, created=False, **kwargs):
    if sender.__name__ not in ALLOWED_SENDERS:
        # Only run on users
        return
    if not created:
        # run only once
        return
    _currencies = Currency.objects.filter(is_crypto=True)
    for currency in _currencies:
        if not currency.disabled:
            create_user_wallet(instance, currency)
