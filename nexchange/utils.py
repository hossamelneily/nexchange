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
from django.utils.log import AdminEmailHandler
from accounts.models import SmsToken
import string

api = Uphold(settings.API1_IS_TEST)
api.auth_basic(settings.API1_USER, settings.API1_PASS)
logging.basicConfig(level=logging.DEBUG)


class Del:
    def __init__(self, keep=string.digits):
        self.comp = dict((ord(c), c) for c in keep)

    def __getitem__(self, k):
        return self.comp.get(k)


def send_email(to, subject='Nexchange', msg=None):
    send_mail(
        subject,
        msg,
        'noreply@nexchange.co.uk',
        [to],
        fail_silently=not settings.DEBUG,
    )


def send_sms(msg, phone):
    if not phone.startswith('+'):
        phone = '+{}'.format(phone)
    if phone.startswith('+1'):
        from_phone = settings.TWILIO_PHONE_FROM_US
    else:
        from_phone = settings.TWILIO_PHONE_FROM_UK
    try:
        client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        message = client.messages.create(
            body=msg, to=phone, from_=from_phone)
        return message
    except TwilioException as err:
        return err


def sanitize_number(phone, is_phone=False):
    keep_numbers = Del()
    phone = phone.translate(keep_numbers)
    if phone.startswith(settings.NUMERIC_INTERNATIONAL_PREFIX):
        phone = phone.replace(settings.NUMERIC_INTERNATIONAL_PREFIX,
                              '')
    return '{}{}'.format(settings.PLUS_INTERNATIONAL_PREFIX
                         if is_phone else '',
                         phone)


def send_auth_sms(user):
    def create_token():
        _token = SmsToken(user=user, send_count=1)
        _token.save()
        return _token
    try:
        token = SmsToken.objects.filter(user=user).latest('id')
        token.send_count += 1
        token.save()
    except SmsToken.DoesNotExist:
        token = create_token()
    if not token.valid:
        token = create_token()

    msg = settings.SMS_MESSAGE_AUTH + '{}'.format(token.sms_token)
    phone_to = str(user.username)

    try:
        client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=msg, to=phone_to, from_=settings.TWILIO_PHONE_FROM)
        return message
    except TwilioException as err:
        raise err


def print_traceback():
    ex_type, ex, tb = sys.exc_info()
    traceback.print_tb(tb)


def release_payment(withdraw, amount, type_='BTC'):
    # TODO: take from user cards
    try:
        txn_id = api.prepare_txn(settings.API1_ID_C1,
                                 withdraw, amount, type_)
        print(txn_id)
        res = api.execute_txn(settings.API1_ID_C1, txn_id)
        print(res)
        return txn_id
    except Exception as e:
        print('error {}'.format(e))
        print_traceback()


def check_address_blockchain(address):
    # TODO: ethereum support
    logger = get_nexchange_logger(__name__, True, True)

    def _set_network(_address):
        _currency = None
        _confirmations = None
        if not address or not address.address:
            return False
        if address.currency:
            _confirmations = address.currency.min_confirmations
            _currency = _address.currency.code.lower()

            if not _currency:
                if not address.currency.flag(__name__)[1]:
                    logger.error('Currency not found for address pk {}'
                                 .format(address.pk))
                return
            elif _currency == 'eth':
                if not address.currency.flag(__name__)[1]:
                    logger.info('Address pk {} of '
                                'unsupported type eth ethereum'
                                .format(address.pk))
                return

        _network = '{}'.format(_currency)
        if settings.DEBUG:
            _network = 't{}'.format(_currency)
        return _network, _confirmations

    def _set_url(_network, wallet_address, _confirmations):
        btc_blockr = (
            'http://{}.blockr.io/api/v1/address/txs/{}?confirmations='
            '{}').format(_network, wallet_address, _confirmations)
        return btc_blockr
    network, confirmations = _set_network(address)
    url = _set_url(network, str(address.address), confirmations)
    info = get(url)
    if info.status_code != 200:
        return False
    transactions = info.json()['data']
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

    tx.confirmations = num_confirmations
    tx.save()

    if num_confirmations > tx.address_to.currency.min_confirmations:
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


class BasePaymentApi:
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


class OkPayAPI(BasePaymentApi):
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

    # def get_date_time(self):
    #     ''' Get the server time in UTC.
    #         Params: None
    #         Returns: String value - Date (YYYY-MM-DD HH:mm:SS)
    #                 2010-12-31 10:33:44'''
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

    def _parse_transaction(self, transaction):
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
            attributes = self._parse_transaction(trans)
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

    def _send_money(self, receiver=None, currency=None, amount=None,
                    comment=None, is_receiver_pays_fees=False, invoice=None):
        """
        https://dev.okpay.com/en/manual/interfaces/functions/general
        /send-money.html
        """

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
                   comment=None, is_receiver_pays_fees=False, invoice=None):
        try:
            service_resp = self._send_money(
                receiver=receiver, currency=currency, amount=amount,
                comment=comment, is_receiver_pays_fees=is_receiver_pays_fees,
                invoice=invoice
            )
            transaction = ET.fromstring(service_resp)[0][0][0]
            res = self._parse_transaction(transaction)
        except WebFault as e:
            res = {'success': 0, 'error': e}
        return res


class PayeerAPIClient(BasePaymentApi):
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

    def get_transaction_history(self, from_date=None, to_date=None,
                                page_size=50, sort='desc',
                                trans_type='incoming'):
        from_date, to_date = self.get_default_ranges(from_date, to_date)

        # to is removed, because it is not UTC on Payeer side.
        payload = {
            'account': self.account,
            'apiId': self.apiId,
            'apiPass': self.apiPass,
            'action': 'history',
            'sort': sort,
            'count': page_size,
            'from': from_date,
            'type': trans_type
        }
        response = requests.post(self.url, payload)
        content = json.loads(response.content.decode('utf-8'))
        try:
            res = content['history']
        except KeyError:
            res = content['errors']
        return res

    def transfer_funds(self, currency_in=None, currency_out=None, amount=None,
                       receiver=None, comment=None):

        payload = {
            'account': self.account,
            'apiId': self.apiId,
            'apiPass': self.apiPass,
            'action': 'transfer',
            'curIn': currency_in,
            'sumOut': amount,
            'curOut': currency_out,
            'comment': comment,
            'to': receiver
        }
        response = requests.post(self.url, payload)
        content = json.loads(response.content.decode('utf-8'))
        return content


def get_nexchange_logger(name, with_console=True, with_email=False):
    formatter_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logger = logging.getLogger(
        name
    )
    logger.level = logging.DEBUG
    formatter = logging.Formatter(formatter_str)
    handlers = []
    if with_console:
        console_ch = logging.StreamHandler(sys.stdout)
        handlers.append((console_ch, 'DEBUG',))

    if with_email and not settings.DEBUG:
        email_ch = AdminEmailHandler()
        handlers.append((email_ch, 'WARNING',))

    for handler, level in handlers:
        level_code = getattr(logging, level, logging.DEBUG)
        handler.setLevel(level_code)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if not handlers:
        print('WARNING: logger with no handlers')
        print_traceback()

    return logger


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip