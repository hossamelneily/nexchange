from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from orders.models import Order
from accounts.models import Balance


@receiver(pre_save, sender=Order)
def calculate_pre_revenue(sender, instance, **kwargs):
    referral = instance.user.referrals_set.last()
    if referral and instance.status == Order.COMPLETED:
        instance.old_referral_revenue = referral.revenue


@receiver(post_save, sender=Order)
def calculate_post_revenue(sender, instance, **kwargs):
    referral = instance.user.referrals_set.last()
    if referral and instance.status == Order.COMPLETED:
        revenue_from_trade = referral.revenue - instance.old_referral_revenue

        balance, created = \
            Balance.objects.get_or_create(user=referral.code.user,
                                          currency=instance.pair.base)
        balance.balance += revenue_from_trade
        balance.save()
