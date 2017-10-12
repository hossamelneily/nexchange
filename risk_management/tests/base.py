from django.test import TestCase


class RiskManagementBaseTestCase(TestCase):

    fixtures = [
        'currency_crypto.json',
        'currency_fiat.json',
        'pairs_cross.json',
        'reserve.json',
        'account.json',
    ]
