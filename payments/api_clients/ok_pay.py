from payments.api_clients.base import BasePaymentApi
from suds import WebFault
import datetime
from hashlib import sha256
import xml.etree.ElementTree as ET


class OkPayAPI(BasePaymentApi):
    def __init__(self, api_password=None, wallet_id=None, url=None):
        ''' Set up your API Access Information
            https://www.okpay.com/en/developers/interfaces/setup.html '''
        super(OkPayAPI, self).__init__()
        if api_password is None:
            self.api_password = 'your details here'
        else:
            self.api_password = api_password
        if wallet_id is None:
            self.wallet_id = 'Your details here'
        else:
            self.wallet_id = wallet_id

        # Generate Security Token
        concatenated = api_password + datetime.datetime.utcnow().strftime(
            ":%Y%m%d:%H"
        )
        concatenated = concatenated.encode('utf-8')
        self.security_token = sha256(concatenated).hexdigest()
        # Create proxy client
        if url is None:
            url = 'https://api.okpay.com/OkPayAPI?singleWsdl'
        self.url = url

    # def get_date_time(self):
    #     ''' Get the server time in UTC.
    #         Params: None
    #         Returns: String value - Date (YYYY-MM-DD HH:mm:SS)
    #                 2010-12-31 10:33:44'''
    #     self._get_client()
    #     response = self.client.service.Get_Date_Time()
    #     root = ET.fromstring(response)
    #     now = root[0][0][0].text
    #     return now

    def get_balance(self, currency=None):
        ''' Get the balance of all currency wallets or of a single currency.
            Params: currency is a three-letter code from the list at
                        https://www.okpay.com/en/developers/currency-codes.html
                        if no currency is passed then all wallet balances are
                        returned.
            Returns: dictionary in the form {'balance': {'CUR': '0.0', ...}}
        '''
        self._get_soap_client()
        try:
            if currency is None:
                response = self.client.service.Wallet_Get_Currency_Balance(
                    self.wallet_id, self.security_token,
                    currency)
                balance = {response.Currency: response.Amount}
            else:
                response = self.client.service.Wallet_Get_Balance(
                    self.wallet_id, self.security_token)
                balance = {
                    item.Currency: item.Amount for item in response.Balance
                }
            response = {'success': 1, 'balance': balance}
        except WebFault as e:
            response = {'success': 0, 'error': e}

        return response

    def _get_transaction_history(self, from_date, to_date, page_size,
                                 page_number):
        """
        https://dev.okpay.com/en/manual/interfaces/functions/general
        /transaction-history.html
        """

        self._get_soap_client()
        response = self.client.service.Transaction_History(
            self.wallet_id,
            self.security_token,
            from_date,
            to_date,
            page_size,
            page_number
        )
        return response

    def _parse_user_data(self, user):
        res = {}
        for i in user:
            res.update({i.tag.split('}')[1]: i.text})
        return res

    def _parse_xml_transaction(self, transaction):
        attributes = {}
        for el in transaction:
            attributes.update({el.tag.split('}')[1]: el.text})
            if el.tag.split('}')[1] == 'Receiver':
                attributes.update({'Receiver': self._parse_user_data(el)})
            elif el.tag.split('}')[1] == 'Sender':
                attributes.update({'Sender': self._parse_user_data(el)})
        return attributes

    def _parse_transactions(self, transactions):
        res = []
        if transactions is None:
            return res
        for trans in transactions:
            attributes = self._parse_xml_transaction(trans)
            res.append(attributes)
        return res

    def get_transaction_history(self, from_date=None, to_date=None,
                                page_size=50, page_number=1):
        from_date, to_date = self.get_default_ranges(from_date, to_date)
        try:
            service_resp = self._get_transaction_history(
                from_date, to_date, page_size, page_number
            )
            root = ET.fromstring(service_resp)[0][0][0]
            res = {}
            for el in root:
                if el.tag.split('}')[1] == 'Transactions':
                    res.update({'Transactions': self._parse_transactions(el)})
                else:
                    res.update({el.tag.split('}')[1]: el.text})
        except WebFault as e:
            res = {'success': 0, 'error': e}
        return res

    def get_transaction(self, transaction_id=None, invoice=None):
        """
        https://dev.okpay.com/en/manual/interfaces/functions/general
        /transaction-get.html
        """
        self._get_soap_client()
        try:
            response = self.client.service.Transaction_Get(
                self.wallet_id,
                self.security_token,
                transaction_id,
                invoice
            )
        except WebFault as e:
            response = {'success': 0, 'error': e}
        return response

    def account_check(self, account):
        """
        https://dev.okpay.com/en/manual/interfaces/functions/general
        /account-check.html
        """
        self._get_soap_client()
        try:
            response = self.client.service.Account_Check(
                self.wallet_id,
                self.security_token,
                account,
            )
        except WebFault as e:
            response = {'success': 0, 'error': e}
        return response

    def _send_money(self, receiver=None, currency=None, amount=None,
                    comment=None, is_receiver_pays_fees=True, invoice=None):
        """
        https://dev.okpay.com/en/manual/interfaces/functions/general
        /send-money.html
        """

        self._get_soap_client()
        response = self.client.service.Send_Money(
            self.wallet_id,
            self.security_token,
            receiver,
            currency,
            amount,
            comment,
            is_receiver_pays_fees,
            invoice
        )
        return response

    def send_money(self, receiver=None, currency=None, amount=None,
                   comment=None, is_receiver_pays_fees=True, invoice=None):
        try:
            service_resp = self._send_money(
                receiver=receiver, currency=currency, amount=amount,
                comment=comment, is_receiver_pays_fees=is_receiver_pays_fees,
                invoice=invoice
            )
            transaction = ET.fromstring(service_resp)[0][0][0]
            res = self._parse_xml_transaction(transaction)
        except WebFault as e:
            res = {'success': 0, 'error': e}
        return res
