from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order
from accounts.models import Balance


@receiver(post_save, sender=Order)
def referral_accounting(sender, instance, **kwargs):
    if len(instance.user.referrals_set.all()):
        # TODO: Add referralTransaction
        new_referral_revenue = instance.user.referrals_set.get().revenue
        revenue_from_trade = \
            new_referral_revenue - instance.old_referral_revenue

        balance, created = \
            Balance.objects.get(user=instance.user, currency=instance.currency)
        balance.balance += revenue_from_trade
        balance.save()
