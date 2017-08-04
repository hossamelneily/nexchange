from core.models import Currency
from django.db.models.signals import post_save
from django.dispatch import receiver
from nexchange.api_clients.rpc import ScryptRpcApiClient
from nexchange.api_clients.uphold import UpholdApiClient

ALLOWED_SENDERS = ['User', 'NexchangeUser']

scrypt_client = ScryptRpcApiClient()
uphold_client = UpholdApiClient()
clients = {scrypt_client.related_nodes[0]: scrypt_client,
           uphold_client.related_nodes[0]: uphold_client}


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
            clients[currency.wallet].create_user_wallet(instance, currency)
