from __future__ import absolute_import
from .base import BasePaymentChecker
from django.conf import settings
from decimal import Decimal
from nexchange.utils import OkPayAPI


class OkPayPaymentChecker(BasePaymentChecker):

    def __init__(self, *args, **kwargs):
        self.name = 'okpay'
        super(OkPayPaymentChecker, self).__init__(*args, **kwargs)
        # Just in case fixtures are inaccurate
        self.allowed_beneficiary.add(settings.OKPAY_WALLET)
        self.api = OkPayAPI(
            api_password=settings.OKPAY_API_KEY,
            wallet_id=settings.OKPAY_WALLET
        )

    def get_transactions(self):
        res = super(OkPayPaymentChecker, self).get_transactions()
        return res['Transactions']

    def transactions_iterator(self):
        for trans in self.transactions:
            yield trans

    def parse_data(self, trans):
        try:
            to = trans['Receiver'].get('WalletID')
            sender = trans['Sender']
            comment, unique_ref = \
                (trans['Comment'], trans['Invoice'],)
            if not unique_ref:
                unique_ref = comment
            if not to:
                to = trans['Receiver']['Email']
            self.data = {
                # required
                'identifier': sender.get('Email', sender['WalletID']),
                'secondary_identifier': trans['Sender']['WalletID'],
                'currency': trans['Currency'],
                'amount_cash': Decimal(trans['Net']),
                'unique_ref': unique_ref,
                'payment_system_id': trans['ID'],
                # essential for checking a transaction
                'is_success': trans['Status'] == 'Completed',
                'beneficiary': to,
                # optional
                'is_verified':
                    sender['VerificationStatus'].lower() == 'verified',
                'comment': comment,
            }
        except KeyError as e:
            self.logger.error("Transaction {} key is missing {}"
                              .format(trans, e))
        except ValueError as e:
            self.logger.error("Transaction {} is not valid for serialization"
                              .format(trans, e))
        super(OkPayPaymentChecker, self).parse_data(trans)
