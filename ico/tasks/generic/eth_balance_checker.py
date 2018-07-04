from .base import BaseIcoManagerTask


class EthBalanceChecker(BaseIcoManagerTask):

    def run(self, subscription_id):
        self.set_eth_balance(subscription_id)
