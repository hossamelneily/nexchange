from django.contrib.auth.models import User
from core.models import Address
from payments.models import UserCards
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from nexchange.utils import CreateUpholdCard


@receiver(post_save, sender=User)
def allocate_wallets(instance, **kwargs):
    currency = {'BTC': 'bitcoin', 'LTC': 'litecoin', 'ETH': 'ethereum'}
    for key, value in currency.items():
        if UserCards.objects.filter(currency=key, user=None).exists():
            card = UserCards.objects.filter(currency=key,
                                            user=None).order_by('id').first()
            card.user = instance
            address = Address(address=card.address_id, user=card.user)
            address.save()
            card.save()
        elif UserCards.objects.filter(currency=key, user=instance).exists():
            pass
        else:
            api = CreateUpholdCard(settings.UPHOLD_IS_TEST)
            api.auth_basic(settings.UPHOLD_USER, settings.UPHOLD_PASS)
            new_card = api.new_card(key)
            address = api.add_address(new_card['id'], value)
            card = UserCards(card_id=new_card['id'],
                             currency=new_card['currency'],
                             address_id=address['id'],
                             user=instance)
            address = Address(address=card.address_id, user=instance)
            address.save()
            card.save()
