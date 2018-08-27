from .base import BaseIcoManagerTask


class CategoryChecker(BaseIcoManagerTask):

    def run(self, subscription_id):
        self.category_check(subscription_id)
