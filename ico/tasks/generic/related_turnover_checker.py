from .base import BaseIcoManagerTask


class RelatedTurnoverChecker(BaseIcoManagerTask):

    def run(self, subscription_id):
        self.set_related_turnover(subscription_id)
