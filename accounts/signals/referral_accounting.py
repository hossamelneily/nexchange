from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from orders.models import Order
from accounts.models import Balance


def __round__(num):
    return round(num)


@receiver(pre_save, sender=Order)
def calculate_pre_revenue(sender, instance, **kwargs):
    referees = instance.user.referrals_set.all()
    if len(referees):
        rev = 0
        for referee in referees:
            rev += referee.revenue
        instance.old_referral_revenue = rev


@receiver(post_save, sender=Order)
def calculate_post_revenue(sender, instance, **kwargs):
    referees = instance.user.referrals_set.all()
    if len(referees):
        # TODO: Add referralTransaction
        new_referral_revenue = 0
        for referee in referees:
            new_referral_revenue += referee.revenue
        revenue_from_trade = \
            new_referral_revenue - instance.old_referral_revenue

        balance, created = \
            Balance.objects.get_or_create(user=instance.user,
                                          currency=instance.pair.base)
        balance.balance += revenue_from_trade
        balance.save()
