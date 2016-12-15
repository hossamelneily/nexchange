from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order
from accounts.models import Balance


@receiver(post_save, sender=Order)
def update_referral_balance(sender):
    if len(sender.user.referral.all()):
        # TODO: Add referralTransaction
        new_referral_revenue = sender.user.referral.get().revenue
        revenue_from_trade = \
            new_referral_revenue - sender.old_referral_revenue

        balance, created = \
            Balance.objects.get(user=sender.user, currency=sender.currency)
        balance.balance += revenue_from_trade
        balance.save()
