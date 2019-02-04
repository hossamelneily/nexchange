from django.test import TestCase
from decimal import Decimal


class RiskManagementBaseTestCase(TestCase):

    fixtures = [
        'transaction_price.json',
        'currency_algorithm.json',
        'currency_crypto.json',
        'currency_fiat.json',
        'currency_tokens.json',
        'pairs_cross.json',
        'reserve.json',
        'account.json',
    ]

    def _get_bittrex_get_balance_response(self, balance, available=None,
                                          pending=None):
        if available is None:
            available = Decimal(balance) * Decimal(0.7)
        if pending is None:
            pending = Decimal(balance) * Decimal(0.3)
        response = {
            'result': {
                'Available': available,
                'Balance': balance,
                'CryptoAddress': 'D8BVYkdLYJozKYURTghmgEKRwHm6tYmLn7',
                'Currency': 'XVG',
                'Pending': pending
            },
            'success': True
        }
        return response

    def _get_bittrex_get_ticker_response(self, ask=None, bid=None, last=None):
        response = {
            'success': True,
            'message': '',
            'result': {
                'Last': 1.07e-06 if last is None else last,
                'Ask': 1.08e-06 if ask is None else ask,
                'Bid': 1.07e-06 if bid is None else bid
            }
        }
        return response
