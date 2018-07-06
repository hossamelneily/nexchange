from .base import BaseIcoManagerTask


class TokenBalanceChecker(BaseIcoManagerTask):

    def run(self, subscription_id):
        self.set_token_balances(subscription_id)
