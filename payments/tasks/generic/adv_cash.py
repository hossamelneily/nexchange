from __future__ import absolute_import
from .base import BasePaymentChecker
from django.conf import settings
from decimal import Decimal
from payments.api_clients.adv_cash import AdvCashAPIClient


class AdvCashPaymentChecker(BasePaymentChecker):

    def __init__(self, *args, **kwargs):
        self.name = 'Advanced Cash'
        super(AdvCashPaymentChecker, self).__init__(*args, **kwargs)
        for wallet in settings.ADV_CASH_WALLETS:
            self.allowed_beneficiary.add(wallet)
        self.api = AdvCashAPIClient(
            api_name=settings.ADV_CASH_API_NAME,
            account_email=settings.ADV_CASH_ACCOUNT_EMAIL,
            api_password=settings.ADV_CASH_API_PASSWORD
        )

    def transactions_iterator(self, direction='INCOMING'):
        for trans in self.transactions:
            if trans['direction'] == direction:
                yield trans

    def parse_data(self, trans):
        try:
            to = trans.get('walletDestId')
            comment, unique_ref = \
                (trans.get('comment'), trans.get('orderId'),)
            if not unique_ref:
                unique_ref = comment
            if not to:
                to = trans['receiverEmail']
            self.data = {
                # required
                'identifier': trans.get('senderEmail',
                                        trans.get('walletSrcId')),
                'secondary_identifier': trans.get('walletSrcId'),
                'currency': trans['currency'],
                'amount_cash': Decimal(trans['amount']),
                'unique_ref': unique_ref,
                'payment_system_id': trans['id'],
                # essential for checking a transaction
                'is_success': trans.get('status') == 'COMPLETED',
                'beneficiary': to,
                # optional
                'comment': comment,
            }
        except KeyError as e:
            self.logger.error("Transaction {} key is missing {}"
                              .format(trans, e))
        except ValueError as e:
            self.logger.error("Transaction {} is not valid for serialization"
                              .format(trans, e))
        super(AdvCashPaymentChecker, self).parse_data(trans)
