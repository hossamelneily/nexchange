from nexchange.tasks.base import BaseTask
from nexchange.api_clients.factory import ApiClientFactory
from core.models import Currency, Transaction
from accounts.models import Balance
from django.db import transaction
from django.conf import settings


class BalancePayoutTask(BaseTask):

    def __init__(self):
        super(BalancePayoutTask, self).__init__()
        self.btc = Currency.objects.get(code='BTC')
        self.api = ApiClientFactory.get_api_client(self.btc.wallet)

    def get_balances(self):
        return Balance.objects.filter(
            currency=self.btc,
            balance__gte=self.btc.minimal_referral_payout
        )

    def payout_balance(self, balance):
        address = balance.user.profile.affiliate_address
        currency = balance.currency
        # FIXME: remove this that balances on production fixed
        assert currency == self.btc
        amount = balance.balance
        comment = 'Referral payout for user {}'.format(balance.user)
        user = balance.user
        profile = user.profile
        if not profile.do_auto_referral_payouts:
            self.logger.info(
                'Cannot pay referrals. User {} profile is not set up to do '
                'auto referral payouts'.format(balance.user)
            )
            return
        if not address:
            self.logger.info(
                'Cannot pay referrals. User {} does not have an '
                'affiliate_address defined'.format(balance.user)
            )
            return
        if address.currency != self.btc:
            self.logger.info(
                'Cannot pay referrals automatically. User {} affiliate '
                'address currency is not BTC'.format(balance.user)
            )
            return

        if profile.monthly_payout_limit_exceeded:
            self.logger.info(
                'In last 30 days referral payouts ({} USD) for user {} '
                'exceeded the LIMIT ({} USD). Automatic payouts '
                'blocked.'.format(
                    profile.last_30_days_payout_usd,
                    profile.user.username,
                    settings.REFERRAL_PAYOUT_30_DAYS_LIMIT_USD
                )
            )

            return

        with transaction.atomic():
            tx = Transaction(
                currency=self.btc, amount=amount,
                type=Transaction.REFERRAL_PAYOUT, address_to=address,
                admin_comment=comment, user=user
            )
            tx.save()
            balance.balance -= amount
            balance.save()
            tx_id, success = self.api.release_coins(tx.currency,
                                                    tx.address_to, tx.amount)
            if success:
                tx.tx_id = tx_id
                tx.save()

    def run(self):
        balances = self.get_balances()
        for balance in balances:
            self.payout_balance(balance)
