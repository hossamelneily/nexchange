from django.db.models.signals import post_save
from django.dispatch import receiver
from core.utils import create_deposit_address

ALLOWED_SENDERS = ['Order', 'LimitOrder']


@receiver(post_save, dispatch_uid='allocate_wallets')
def allocate_wallets(sender, instance=None, created=False, **kwargs):
    if sender.__name__ not in ALLOWED_SENDERS:
        # Only run on users
        return
    if not created:
        return
    order = instance
    user = order.user
    currency = \
        order.pair.base if order.order_type == order.SELL else order.pair.quote
    if user is None:
        return
    if not all([
        currency.is_crypto,
        not currency.disabled,
        currency.is_quote_of_enabled_pair_for_test,
    ]):
        # FIXME: Here we can add some message to our customer. Uphold is doing
        # that. It is something like - 'Sorry, our payment provider
        # currently is dealing with some technical issues/We do not support
        # this currency at the time.'
        return
    if not order.deposit_address:
        create_deposit_address(user, order)
