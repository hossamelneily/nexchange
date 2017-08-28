import json
from core.tests.base import OrderBaseTestCase
from django.core.urlresolvers import reverse
from unittest import skip


class PairsTestCase(OrderBaseTestCase):

    def setUp(self):
        super(PairsTestCase, self).setUp()
        self.url = reverse('pair-list')
        self.pairs = json.loads(
            self.client.get(self.url).content.decode('utf-8')
        )

    def test_pairs_without_params_should_return_all_pairs(self):
        self.assertGreater(len(self.pairs), 0)

    def check_pair_data(self, pair):
        self.assertEqual(pair['base'] + pair['quote'], pair['name'])
        self.assertGreater(float(pair['fee_ask']), 0)
        self.assertGreater(float(pair['fee_bid']), 0)

        for key in pair:
            self.assertIsNotNone(pair[key])

    def test_pairs_without_params_list_correct_fields(self):
        for pair in self.pairs:
            self.check_pair_data(pair)

        self.assertGreater(len(self.pairs), 0)

    @skip('Breaks when caching is on')
    def test_pairs_detail_should_return_single_pair(self):
        for pair in self.pairs:
            pair_detail_url = reverse(
                'pair-detail', kwargs={'name': pair['name']})
            pair_detail = json.loads(
                self.client.get(pair_detail_url).content.decode('utf-8')
            )

            self.check_pair_data(pair_detail)
