from core.models import Address, Currency
from payments.models import UserCards
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from nexchange.utils import CreateUpholdCard, get_nexchange_logger
import sys

ALLOWED_SENDERS = ['User', 'NexchangeUser']
logger = get_nexchange_logger('allocate_wallets', True, True)


@receiver(post_save, dispatch_uid='allocate_wallets')
def allocate_wallets(sender, instance=None, created=False, **kwargs):
    if 'test' in sys.argv:
        # hacky way to bypass tests
        return
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
        elif UserCards.objects.filter(currency=key, user=instance).exists():
            pass
        else:
            api = CreateUpholdCard(settings.API1_IS_TEST)
            api.auth_basic(settings.API1_USER, settings.API1_PASS)
            new_card = api.new_card(key)
            if 'id' not in new_card:
                logger.error('new card creation failed {}'.format(new_card))
                return
            address = api.add_address(new_card['id'], value)
            card = UserCards(card_id=new_card['id'],
                             currency=new_card['currency'],
                             address_id=address['id'],
                             user=instance)
            address = Address(
                address=card.address_id,
                user=instance,
                currency=currency,
                type=Address.DEPOSIT
            )
            address.save()
            card.save()
