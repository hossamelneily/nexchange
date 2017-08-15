from django.db.models.signals import post_save
from django.dispatch import receiver
from nexchange.api_clients.rpc import ScryptRpcApiClient
from nexchange.api_clients.uphold import UpholdApiClient

ALLOWED_SENDERS = ['Order']

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
        return
    order = instance
    user = order.user
    currency = order.pair.quote
    if user is None:
        return
    if currency.disabled or not currency.is_crypto:
        # FIXME: Here we can add some message to our customer. Uphold is doing
        # that. It is something like - 'Sorry, our payment provider
        # currently is dealing with some technical issues/We do not support
        # this currency at the time.'
        return
    card, address = clients[currency.wallet].create_user_wallet(user, currency)
    order.deposit_address = address
    order.save()
