from django.conf import settings
from suds.client import Client
from nexchange.utils import get_nexchange_logger
import datetime


class BasePaymentApi:

    def __init__(self):
        self.logger = get_nexchange_logger(
            self.__class__.__name__,
            True,
            True
        )
        self.client = None

    def get_transaction_history(self):
        raise NotImplementedError

    def get_default_ranges(self, from_date, to_date):
        if to_date is None:
            to_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if from_date is None:
            default_from_time = (datetime.datetime.now() -
                                 settings.PAYMENT_DEFAULT_SEEK_INTERVAL)
            from_date = default_from_time.strftime('%Y-%m-%d %H:%M:%S')

        return from_date, to_date

    def _get_soap_client(self):
        if self.client is None:
            self.client = Client(
                url=self.url,
                retxml=True
            )

    def _parse_xml_transaction(self, transaction):
        attributes = {}
        for el in transaction:
            attributes.update({el.tag: el.text})
        return attributes

    def _parse_xml_transactions(self, transactions):
        res = []
        if transactions is None:
            return res
        for trans in transactions:
            attributes = self._parse_xml_transaction(trans)
            res.append(attributes)
        return res
