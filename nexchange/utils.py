import sys
import traceback
import logging
from django.conf import settings
from django.core.mail import send_mail
from requests import get
from twilio.exceptions import TwilioException
from twilio.rest import TwilioRestClient

from uphold import Uphold
from suds.client import Client
from suds import WebFault
import datetime
from hashlib import sha256
import xml.etree.ElementTree as ET
import requests
import json

api = Uphold(settings.UPHOLD_IS_TEST)
api.auth_basic(settings.UPHOLD_USER, settings.UPHOLD_PASS)


def send_email(to, subject='Nexchange', msg=None):
    send_mail(
        subject,
        msg,
        'noreply@nexchange.ru',
        [to],
        fail_silently=not settings.DEBUG,
    )


def send_sms(msg, phone):
    try:
        client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        message = client.messages.create(
            body=msg, to=phone, from_=settings.TWILIO_PHONE_FROM)
        return message
    except TwilioException as err:
        return err


def release_payment(withdraw, amount, type_='BTC'):
    # TODO: take from user cards
    try:
        txn_id = api.prepare_txn(settings.UPHOLD_CARD_ID_BTC,
                                 withdraw, amount, type_)
        print(txn_id)
        res = api.execute_txn(settings.UPHOLD_CARD_ID_BTC, txn_id)
        print(res)
        return txn_id
    except Exception as e:
        print('error {}'.format(e))
        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)


def check_address_blockchain(address, confirmed=True):
    def _set_network(_address):
        if not address or not address.address:
            return False
        currency = 'btc'
        if address.currency:
            currency = _address.currency.code.lower()
        _network = '{}'.format(currency)
        if settings.DEBUG:
            _network = 't{}'.format(currency)
        return _network

    def _set_url(_network, wallet_address):
        btc_blockr = 'http://{}.blockr.io/api/v1/address/txs/{}'. \
            format(_network, wallet_address)
        return btc_blockr
    network = _set_network(address)
    url = _set_url(network, str(address.address))
    info = get(url)
    if info.status_code != 200:
        return False
    transactions = info.json()['data']['txs']
    if confirmed:
        for trans in transactions:
            if trans['confirmations'] > settings.MIN_REQUIRED_CONFIRMATIONS:
                continue
            else:
                transactions.remove(trans)
    return transactions


def check_transaction_blockchain(tx):
    if not tx or not tx.tx_id:
        return False
    currency = 'btc'
    if tx.address_to.currency:
        currency = tx.address_to.currency.code.lower()
    network = '{}'.format(currency)
    if settings.DEBUG:
        network = 't{}'.format(currency)
    btc_blockr = 'http://{}.blockr.io/api/v1/tx/info/{}'.\
        format(network, str(tx.tx_id))
    info = get(btc_blockr)
    if info.status_code != 200:
        return False
    num_confirmations = int(info.json()['data']['confirmations'])
    if num_confirmations > settings.MIN_REQUIRED_CONFIRMATIONS:
        return True
    else:
        return False


def check_transaction_uphold(tx):
    if not tx:
        return False

    res = api.get_reserve_transaction(tx.tx_id_api)
    if not tx.tx_id:
        tx.tx_id = res.\
            get('params', {}).\
            get('txid')
    print("status: {}".format(res.get('status')))
    return res.get('status') == 'completed'


class CreateUpholdCard(Uphold):

    def new_card(self, currency):
        """
        Create a new card
        """

        fields = {
            'label': 'User card',
            'currency': currency,
        }
        return self._post('/me/cards/', fields)

    def add_address(self, card, network):
        """
        Add to card address
        """

        fields = {
            'network': network,
        }
        return self._post('/me/cards/{}/addresses'.format(card), fields)


class OkPayAPI(object):

    def __init__(self, api_password=None, wallet_id=None):
        ''' Set up your API Access Information
            https://www.okpay.com/en/developers/interfaces/setup.html '''
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
        self.client = Client(
            url='https://api.okpay.com/OkPayAPI?singleWsdl',
            retxml=True
        )

    def get_date_time(self):
        ''' Get the server time in UTC.
            Params: None
            Returns: String value - Date (YYYY-MM-DD HH:mm:SS)
                    2010-12-31 10:33:44 '''
        response = self.client.service.Get_Date_Time()
        root = ET.fromstring(response)
        now = root[0][0][0].text
        return now

    def get_balance(self, currency=None):
        ''' Get the balance of all currency wallets or of a single currency.
            Params: currency is a three-letter code from the list at
                        https://www.okpay.com/en/developers/currency-codes.html
                        if no currency is passed then all wallet balances are
                        returned.
            Returns: dictionary in the form {'balance': {'CUR': '0.0', ...}}
        '''
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

    def _get_transaction_history(self, from_date, till_date, page_size,
                                 page_number):
        """
        https://dev.okpay.com/en/manual/interfaces/functions/general
        /transaction-history.html
        """
        response = self.client.service.Transaction_History(
            self.wallet_id,
            self.security_token,
            from_date,
            till_date,
            page_size,
            page_number)
        return response

    def _parse_user_data(self, user):
        res = {}
        for i in user:
            res.update({i.tag.split('}')[1]: i.text})
        return res

    def _parse_transactions(self, transactions):
        res = []
        if transactions is None:
            return res
        for trans in transactions:
            attributes = {}
            for el in trans:
                attributes.update({el.tag.split('}')[1]: el.text})
                if el.tag.split('}')[1] == 'Receiver':
                    attributes.update({'Receiver': self._parse_user_data(el)})
                elif el.tag.split('}')[1] == 'Sender':
                    attributes.update({'Sender': self._parse_user_data(el)})
            res.append(attributes)
        return res

    def get_transaction_history(self, page_size=50, page_number=1):
        from_date = '2011-05-16 10:22:33'
        till_date = self.get_date_time()
        try:
            service_resp = self._get_transaction_history(
                from_date, till_date, page_size, page_number
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
        try:
            response = self.client.service.Account_Check(
                self.wallet_id,
                self.security_token,
                account,
            )
        except WebFault as e:
            response = {'success': 0, 'error': e}
        return response


class PayeerAPIClient(object):
    """ Documentation: http://docs.payeercom.apiary.io/# """

    def __init__(self, account='12345', apiId='12345', apiPass='12345',
                 url='https://payeer.com/ajax/api/api.php'):
        self.account = account
        self.apiId = apiId
        self.apiPass = apiPass
        self.url = url

    def authorization_check(self):
        payload = {
            'account': self.account,
            'apiId': self.apiId,
            'apiPass': self.apiPass
        }
        response = requests.post(self.url, payload)
        return response

    def balance_check(self):
        payload = {
            'account': self.account,
            'apiId': self.apiId,
            'apiPass': self.apiPass,
            'action': 'balance'
        }
        response = requests.post(self.url, payload)
        return response

    def history_of_transactions(self, sort='desc', count=10, to_dt=None,
                                trans_type='incoming'):
        if to_dt is None:
            to_dt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        payload = {
            'account': self.account,
            'apiId': self.apiId,
            'apiPass': self.apiPass,
            'action': 'history',
            'sort': sort,
            'count': count,
            'to': to_dt,
            'type': trans_type
        }
        response = requests.post(self.url, payload)
        content = json.loads(response.content.decode('utf-8'))
        try:
            res = content['history']
        except KeyError:
            res = content['errors']
        return res


def validate_payment_matches_order(order, payment, verbose_match, logger):
    details_match =\
        order.currency == payment.currency and\
        order.amount_cash == payment.amount_cash

    ref_matches = order.unique_reference == payment.reference or \
        (verbose_match and not payment.reference)

    user_matches = not payment.user or payment.user == order.user

    if not user_matches:
        logger.error('order: {} payment: {} NO USER MATCH'.
                     format(order, payment))
    if not details_match:
        logger.error('order: {} payment: {} NO DETAILS MATCH'.
                     format(order, payment))
    if not ref_matches:
        logger.error('order: {} payment: {} NO REFERENCE MATCH'.
                     format(order, payment))
    elif verbose_match:
        logger.info('order: {} payment: {} NO REFERENCE MATCH,'
                    'RELEASE BY VERBOSE_MATCH (cross reference)'.
                    format(order, payment))

    return user_matches and details_match and ref_matches


def get_nexchange_logger(name):
    logger = logging.getLogger(
        name
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s'
                                  ' - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger
