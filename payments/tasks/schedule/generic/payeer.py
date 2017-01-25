from __future__ import absolute_import
from .base import BasePaymentChecker
from django.conf import settings
from decimal import Decimal
from nexchange.utils import PayeerAPIClient
import re


class PayeerPaymentChecker(BasePaymentChecker):

    def __init__(self, *args, **kwargs):
        self.name = 'payeer'
        super(PayeerPaymentChecker, self).__init__(*args, **kwargs)

        self.api = PayeerAPIClient(
            account=settings.PAYEER_ACCOUNT,
            apiId=settings.PAYEER_API_ID,
            apiPass=settings.PAYEER_API_KEY,
            url=settings.PAYEER_API_URL
        )

    def get_transactions(self):
        self.transactions = self.api.history_of_transactions()

    def transactions_iterator(self):
        for tid in self.transactions:
            yield self.transactions[tid]

    def validate_beneficiary(self, trans):
        try:
            to = trans['to']
        except KeyError:
            self.logger.error('transaction {} beneficiary was not in response'
                              .format(trans))
            return False

        return to in [settings.PAYEER_ACCOUNT,
                      self.payment_preference.identifier]

    def validate_success(self, trans):
        return trans['status'] == 'success'

    def parse_data(self, trans, res=None):
        try:
            email = re.findall(r'[\w\.-]+@[\w\.-]+',
                               trans.get('comment', '')).pop()
        except IndexError:
            email = None
            self.logger.error(
                'Unable to extract Payeer email {}'.format(trans))

        try:
            wallet = re.findall(r'P\d+', trans.get('comment', '')).pop()
        except IndexError:
            wallet = None
            t_from = trans.get('from')
            # check if user is not making payment from the merchant
            if t_from and '@merchant' not in t_from:
                wallet = t_from
            self.logger.error('Unable to extract Payeer wallet {}, '
                              'falling back to {}'.format(trans, t_from))

            if not wallet and not email:
                msg = 'Did not find neither email or wallet ' \
                      'id in transaction {}, ' \
                      'kipping payment'.format(self.data)
                self.logger(msg)
                raise ValueError(msg)

        self.data = {
            'identifier': email if email else wallet,
            'secondary_identifier': wallet if email else None,
            'currency': trans['creditedCurrency'],
            'amount_cash': Decimal(trans['creditedAmount']),
            'unique_ref': trans['shopOrderId'],
            'payment_system_id': trans['id'],
            'comment': trans['comment']
        }
        super(PayeerPaymentChecker, self).parse_data(trans)
