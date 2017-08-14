from payments.api_clients.base import BasePaymentApi
import hashlib
from datetime import datetime
import xml.etree.ElementTree as ET


class AdvCashAPIClient(BasePaymentApi):

    def __init__(self, api_name='api_name', account_email='account@email',
                 api_password='api_password'):
        super(AdvCashAPIClient, self).__init__()
        self.url = "https://wallet.advcash.com/wsm/merchantWebService?wsdl"
        self.api_name = api_name
        self.account_email = account_email
        self.api_password = api_password

        self.arg0 = {
            "apiName": self.api_name,
            "authenticationToken": self.getAuthenticationToken(
                self.api_password),
            "accountEmail": self.account_email
        }

    def getAuthenticationToken(self, password):
        currentUTCDate = datetime.utcnow().strftime("%Y%m%d:%H")
        to_hash = (password + ":" + currentUTCDate).encode('utf-8')
        return hashlib.sha256(to_hash).hexdigest()

    def getBalances(self):
        self._get_soap_client()
        return self.client.service.getBalances(arg0=self.arg0)

    def _send_money(self, sendMoneyData):
        """
        Example:
            _send_money({'amount': '100.00', 'currency': 'EUR',
                         'email': 'sender@email.com', 'note': 'Some Payment'})
        Args:
            sendMoneyData: dict with filter parameters

        Returns:
            XML object described in Transaction History chapter of
            https://advcash.com/files/documents/advcash.merchantapi-1.9_en.pdf
        """
        self._get_soap_client()
        return self.client.service.sendMoney(
            arg0=self.arg0, arg1=sendMoneyData)

    def history(self, history_filter):
        """
        Example:
            history({'count': 5})

        Args:
            history_filter: dict with filter parameters

        Returns:
            XML object described in Transaction History chapter of
            https://advcash.com/files/documents/advcash.merchantapi-1.9_en.pdf

        """
        self._get_soap_client()
        return self.client.service.history(arg0=self.arg0, arg1=history_filter)

    def get_transaction_history(self, from_date=None, to_date=None,
                                count=100, transaction_type='ALL'):
        history_filter = {
            'transactionStatus': 'COMPLETED',
            'count': count,
            'transactionName': transaction_type
        }
        from_date, to_date = self.get_default_ranges(from_date, to_date)
        if from_date is not None:
            history_filter.update(
                {'startTimeFrom': from_date.replace(' ', 'T')}
            )
        if to_date is not None:
            history_filter.update({'startTimeTo': to_date.replace(' ', 'T')})
        service_resp = self.history(history_filter)
        xml_transactions = ET.fromstring(service_resp)[0][0]
        transactions = self._parse_xml_transactions(xml_transactions)
        return transactions

    def send_money(self, amount, currency,
                   receiver_email='sarunas@nexchange.co.uk',
                   receiver_wallet=None, note=None):
        data = {
            'amount': amount,
            'currency': currency,
        }
        if receiver_email is not None:
            data.update({'email': receiver_email})
        if receiver_wallet is not None:
            data.update({'walletId': receiver_wallet})
        if note is not None:
            data.update({'note': note})
        try:
            service_resp = self._send_money(data)
            tx_id = ET.fromstring(service_resp)[0][0][0].text
        except Exception as e:
            msg = 'Cannot send Advanced Cash funds. Error: {}'.format(e)
            res = {'status': 'ERROR', 'message': msg}
            self.logger.error(msg)
        else:
            res = {'status': 'OK', 'transaction_id': tx_id}
        return res
