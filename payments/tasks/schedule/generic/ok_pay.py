from __future__ import absolute_import
from .base import BasePaymentChecker
from django.conf import settings
from decimal import Decimal
from nexchange.utils import OkPayAPI


class OkPayPaymentChecker(BasePaymentChecker):

    def __init__(self, *args, **kwargs):
        self.name = 'okpay'
        super(OkPayPaymentChecker, self).__init__(*args, **kwargs)

        self.api = OkPayAPI(
            api_password=settings.OKPAY_API_KEY,
            wallet_id=settings.OKPAY_WALLET
        )

    def get_transactions(self):
        self.transactions = \
            self.api.get_transaction_history()['Transactions']

    def transactions_iterator(self):
        for trans in self.transactions:
            yield trans

    def validate_beneficiary(self, trans):
        try:
            to = trans['Receiver']['WalletID']
        except KeyError:
            return False

        return to in [settings.OKPAY_WALLET,
                      self.payment_preference.identifier]

    def validate_success(self, trans):
        return trans['Status'] == 'Completed'

    def parse_data(self, trans):
        self.data = {
            'identifier': trans['Sender']
            .get('Email', trans['Sender']['WalletID']),
            'secondary_identifier': trans['Sender']['WalletID'],
            'beneficiary': trans['Sender']['VerificationStatus'],
            'verification_status': trans['Sender']['VerificationStatus'],
            'currency': trans['Currency'],
            'amount_cash': Decimal(trans['Net']),
            'unique_ref': trans['Comment'],
            'payment_system_id': trans['ID']
        }
        super(OkPayPaymentChecker, self).parse_data(trans)
