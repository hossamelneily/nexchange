from .base import BaseIcoManagerTask


class AddressTurnoverChecker(BaseIcoManagerTask):

    def run(self, subscription_id):
        self.set_address_turnover(subscription_id)
