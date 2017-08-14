from __future__ import absolute_import
from .base import BasePaymentChecker
from django.conf import settings
from decimal import Decimal
from payments.api_clients.payeer import PayeerAPIClient
import re


class PayeerPaymentChecker(BasePaymentChecker):
    def __init__(self, *args, **kwargs):
        self.name = 'payeer'
        super(PayeerPaymentChecker, self).__init__(*args, **kwargs)
        # Just in case fixtures are inaccurate
        self.allowed_beneficiary.add(settings.PAYEER_ACCOUNT)
        self.api = PayeerAPIClient(
            account=settings.PAYEER_ACCOUNT,
            apiId=settings.PAYEER_API_ID,
            apiPass=settings.PAYEER_API_KEY,
            url=settings.PAYEER_API_URL
        )

    def transactions_iterator(self):
        for tid in self.transactions:
            yield self.transactions[tid]

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

        try:
            self.data = {
                # essential
                'identifier': email if email else wallet,
                'secondary_identifier': wallet if email else None,
                'currency': trans['creditedCurrency'],
                'amount_cash': Decimal(trans['creditedAmount']),
                'unique_ref': trans.get('shopOrderId', trans['comment']),
                'payment_system_id': trans['id'],
                # essential for checking a transaction
                'is_success': trans['status'] == 'success',
                'beneficiary': trans['to'],
                # optional
                'comment': trans['comment'],

            }
        except KeyError as e:
            self.logger.error("Transaction {} key is missing {}"
                              .format(trans, e))
        except ValueError as e:
            self.logger.error("Transaction {} is not valid for serialization"
                              .format(trans, e))
        super(PayeerPaymentChecker, self).parse_data(trans)
