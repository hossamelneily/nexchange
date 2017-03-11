from core.models import Address, Currency
from payments.models import UserCards
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
    _currencies = {'BTC': 'bitcoin', 'LTC': 'litecoin', 'ETH': 'ethereum'}
    for key, value in _currencies.items():
        try:
            currency = Currency.objects.get(code=key.upper())
        except Currency.DoesNotExist:
            logger.error('Currency {} does not exist'.format(key))
            continue
        unassigned_cards = UserCards.objects.filter(currency=key, user=None)
        if len(unassigned_cards) == 0:
            logger.error('{}'.format(instance))
            unassigned_cards = UserCards.objects.filter(currency=key,
                                                        user=None)
            logger.error('{}'.format(unassigned_cards))
            renew_cards_reserve()

        if unassigned_cards.exists():
            # FIFO
            card = unassigned_cards.earliest('id')
            card.user = instance
            address = Address(
                address=card.address_id,
                user=card.user,
                currency=currency,
                type=Address.DEPOSIT
            )
            address.save()
            card.save()
