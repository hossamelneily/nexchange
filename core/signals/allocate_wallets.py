from core.models import Address, AddressReserve, Currency
from django.db.models.signals import post_save
from django.dispatch import receiver
from nexchange.utils import get_nexchange_logger
from accounts.tasks.generate_wallets import renew_cards_reserve

ALLOWED_SENDERS = ['User', 'NexchangeUser']
logger = get_nexchange_logger('allocate_wallets', True, True)


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
        unassigned_cards = AddressReserve.objects.filter(currency=currency,
                                                         user=None)
        logger.warning('instance {} has no reserve cards available'
                       'calling renew_cards_reserve()'
                       .format(instance))
        if len(unassigned_cards) == 0:
            renew_cards_reserve()
            unassigned_cards = AddressReserve.objects.filter(currency=currency,
                                                             user=None)

        if unassigned_cards:
            # FIFO
            card = unassigned_cards.earliest('id')
            card.user = instance
            address = Address(
                address=card.address,
                user=card.user,
                currency=currency,
                type=Address.DEPOSIT,
                reserve=card
            )
            address.save()
            card.save()
        else:
            logger.error('instance {} has no cards available'
                         .format(instance))
