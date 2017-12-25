from django.core.management import BaseCommand
from referrals.models import Referral
from decimal import Decimal
from orders.models import Order


class Command(BaseCommand):
    help = "Check referral stats"

    def get_non_null_codes(self):
        referrals = Referral.objects.all()
        return set(ref.code for ref in referrals if ref.turnover)

    def print_code_info(self, code, i=0, from_ref_pk=0):
        user = code.user
        affiliate_currency = None
        affiliate_address = user.profile.affiliate_address
        if not affiliate_address:
            order = Order.objects.filter(user=user).last()
            if order:
                affiliate_address = order.withdraw_address
        if affiliate_address:
            affiliate_currency = affiliate_address.currency
        refs = code.referral_set.all()
        last_ref_id = refs.latest('id').pk
        turnover = Decimal('0')
        revenue = Decimal('0')
        latest_order_id = 1
        for ref in refs:
            if not ref.orders:
                continue
            if ref.pk <= from_ref_pk:
                continue
            turnover += ref.turnover
            revenue += ref.revenue
            latest_pk = ref.orders.latest('id').pk
            latest_order_id = \
                latest_pk if latest_pk > latest_order_id else latest_order_id

        print(i + 1, code.code, user.username, user.email, turnover, revenue,
              from_ref_pk, last_ref_id, latest_order_id, affiliate_currency,
              affiliate_address)

    def handle(self, *args, **options):
        non_null_ref_codes = self.get_non_null_codes()
        for i, code in enumerate(non_null_ref_codes):
            self.print_code_info(code, i=i)
