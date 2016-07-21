from django.test import TestCase
import requests
import requests_mock
from ticker.models import Price


class TestPrice(TestCase):
    def setUp(self):
        self.adapter = requests_mock.Adapter()
        self.session = requests.session()
        self.session.mount('mock', self.adapter)

    def test_eur_price(self):
        test_eur_usd = 1.5
        test_usd_price = 600.00
        test_rub_price = 40000.00
        self.adapter.register_uri('GET', Price.EUR_RESOURCE,
                                  {'rates': {'USD': test_eur_usd}})

        p = Price(price_usd=test_usd_price, price_rub=test_rub_price)
        p.save()

        self.assertEqual(p.rate_eur, test_eur_usd * p.rate_usd)
        self.assertEqual(p.price_eur, p.price_usd / test_eur_usd)

    def test_usd_price(self):
        test_usd_rub = 60.00
        test_rub_price = 40000.00
        test_usd_price = test_rub_price / test_usd_rub

        p = Price(price_usd=test_usd_price, price_rub=test_rub_price)
        p.save()

        self.assertEqual(p.rate_usd, test_usd_rub)
