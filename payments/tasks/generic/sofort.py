from __future__ import absolute_import
from .base import BasePaymentChecker
from django.conf import settings
from decimal import Decimal
from payments.api_clients.sofort import SofortAPIClient


class SofortPaymentChecker(BasePaymentChecker):
    def __init__(self, *args, **kwargs):
        self.name = 'sofort'
        self.payment_time_property = 'api_time_iso_8601'
        super(SofortPaymentChecker, self).__init__()
        # Just in case fixtures are inaccurate
        self.allowed_beneficiary.add(settings.SOFORT_PROJECT_ID)
        self.allowed_beneficiary.add('YOA LTD')

        self.api = SofortAPIClient()

    def transactions_iterator(self):
        for tx in self.transactions['transactions']:
            yield tx

    def get_transactions(self):
        return self.api.get_transaction_history(start_time=self.start_time)

    def parse_data(self, trans, res=None):
        try:
            self.data = {
                # essential
                'identifier': trans['sender']['holder'],
                'secondary_identifier': trans['sender']['iban'],
                'currency': trans['currency_code'],
                'amount_cash': Decimal(trans['amount']),
                'unique_ref': trans['reasons']['reason'],
                'payment_system_id': trans['transaction'],
                # essential for checking a transaction
                # FIXME: need to discuss with Oleg
                'is_success': True,
                'beneficiary': trans['project_id']

            }
        except KeyError as e:
            self.logger.error("Transaction {} key is missing {}"
                              .format(trans, e))
        except ValueError as e:
            self.logger.error("Transaction {} is not valid for serialization"
                              .format(trans, e))
        super(SofortPaymentChecker, self).parse_data(trans)
