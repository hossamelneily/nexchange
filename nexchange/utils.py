import sys
import traceback
import logging
import base64
import hashlib
import string
from requests import get
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from twilio.exceptions import TwilioException
from twilio.rest import TwilioRestClient
from django.utils.log import AdminEmailHandler
from django.core.mail.message import EmailMessage
from decimal import Decimal
from Crypto import Random
from Crypto.Cipher import AES
from iptools import IpRange
import re


class Del:
    def __init__(self, keep=string.digits):
        self.comp = dict((ord(c), c) for c in keep)

    def __getitem__(self, k):
        return self.comp.get(k)


def send_email(to, subject='n.exchange', msg=None,
               reply_to=('noreply@n.exchange',)):
    mail = EmailMessage(to=(to,),
                        subject=subject,
                        body=msg,
                        reply_to=reply_to,
                        )
    try:
        mail.send(fail_silently=not settings.DEBUG)
        return True
    except TypeError:
        # this is o avoid stopping proccesess on email server failure
        return False



def _send_sms(msg, phone_to, from_phone):
    try:
        client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=msg, to=phone_to, from_=from_phone)
        return message
    except TwilioException as err:
        raise err


def send_sms(msg, phone):
    if not phone.startswith('+'):
        phone = '+{}'.format(phone)
    if phone.startswith('+1'):
        from_phone = settings.TWILIO_PHONE_FROM_US
    else:
        from_phone = settings.TWILIO_PHONE_FROM_UK
    message = _send_sms(msg, phone, from_phone)
    return message


def sanitize_number(phone, is_phone=False):
    keep_numbers = Del()
    phone = phone.translate(keep_numbers)
    if phone.startswith(settings.NUMERIC_INTERNATIONAL_PREFIX):
        phone = phone.replace(settings.NUMERIC_INTERNATIONAL_PREFIX,
                              '')
    return '{}{}'.format(settings.PLUS_INTERNATIONAL_PREFIX
                         if is_phone else '',
                         phone)


def get_traceback():
    ex_type, ex, tb = sys.exc_info()
    return traceback.format_tb(tb)


def check_address_blockchain(address):
    # TODO: ethereum support
    logger = get_nexchange_logger(__name__, True, True)

    def _set_network(_address):
        _currency = None
        _confirmations = None
        if not _address or not _address.address:
            error = 'No address for setting  blockchain Network'
            logger.error(error)
            return error
        if address.currency:
            _confirmations = address.currency.min_confirmations
            _currency = _address.currency.code.lower()

            if not _currency:
                error = 'Currency not defined Error'
                if not address.currency.flag(__name__)[1]:
                    error = (
                        'Currency not found for address pk {}'.format(
                            address.pk
                        )
                    )
                logger.error(error)
                return error
            elif _currency == 'eth':
                error = 'ETH not supported'
                if not address.currency.flag(__name__)[1]:
                    error = ('Address pk {} of unsupported type eth '
                             'ethereum'.format(address.pk))
                logger.info(error)
                return error

        _network = '{}'.format(_currency)
        if settings.DEBUG:
            _network = 't{}'.format(_currency)
        return _network, _confirmations

    def _set_url(_network, wallet_address, _confirmations):
        btc_blockr = (
            'http://{}.blockr.io/api/v1/address/txs/{}?confirmations='
            '{}').format(_network, wallet_address, _confirmations)
        return btc_blockr
    try:
        netwrk = _set_network(address)
        network, confirmations = netwrk
    except ValueError:
        return {'error': 'Cannot set network for blockchain {}'.format(netwrk)}
    url = _set_url(network, str(address.address), confirmations)
    info = get(url)
    if info.status_code != 200:
        return {'error': 'Bad blockchain response status {}.'.format(
            info.status_code
        )}
    transactions = info.json()['data']
    return transactions


def get_transaction_blockchain(_curr, tx_id):
    resource = ''
    curr = _curr.lower()
    logger = get_nexchange_logger(__name__)
    if _curr.upper() == 'BTC':
        resource = 'https://blockexplorer.com/api/tx/{}'.\
            format(tx_id)
    elif _curr.upper() == 'BCH':
        resource = 'https://bitcoincash.blockexplorer.com/api/tx/{}'.format(
            tx_id)
    elif _curr.upper() in ['ETH', 'LTC']:
        resource = 'https://api.blockcypher.com/v1/{}/main/txs/{}'\
            .format(curr, tx_id)

    if not resource:
        logger.warning('get_transaction_blockchain does not support {}'
                       .format(_curr))
        return None, 0
    else:
        res = get(resource)
        parsed_res = res.json()
        return res, parsed_res.get('confirmations', 0)


def check_transaction_blockchain(tx):
    if not tx or not tx.tx_id:
        return 0
    currency = tx.address_to.currency.code.lower()

    return get_transaction_blockchain(currency, str(tx.tx_id))


def get_address_transaction_ids_blockchain(_curr, address_hash):
    def convert_value_int_to_decimal(_network, _value_int):
        if _network in ['ETH']:
            return Decimal(_value_int) / Decimal(1e18)
        elif _network in ['BTC', 'LTC']:
            return Decimal(_value_int) / Decimal(1e8)

    txs = []
    curr = _curr.lower()
    network = _curr.upper()
    txn_prefix = ''
    if network == 'ETH':
        txn_prefix = '0x'

    logger = get_nexchange_logger(__name__)
    if _curr.upper() in ['BTC', 'ETH', 'LTC']:
        resource = 'https://api.blockcypher.com/v1/{}/main/addrs/{}'.format(
            curr, address_hash)
        res = get(resource)
        parsed_res = res.json()
        txns = parsed_res.get('txrefs', [])
        for txn in txns:
            txn_hash = txn.get('tx_hash', None)
            income = txn.get('tx_input_n', 0) == -1
            if txn_hash is not None and income:
                value_int = txn['value']
                amount = convert_value_int_to_decimal(network, value_int)
                txs.append({
                    'tx_id': txn_prefix + txn_hash,
                    'amount': amount
                })
            return res, txs
    elif _curr.upper() in ['BCH']:
        resource = 'https://bitcoincash.blockexplorer.com/api/addr/{}/utxo'.\
            format(address_hash)
        res = get(resource)
        txns = res.json()
        for txn in txns:
            txn_hash = txn.get('txid', None)
            if txn_hash is not None:
                amount = Decimal(str(txn.get('amount', 0)))
                txs.append({
                    'tx_id': txn_prefix + txn_hash,
                    'amount': amount
                })
            return res, txs
    else:
        logger.warning(
            'get_address_transaction_ids_blockchain does not support '
            '{}'.format(_curr)
        )
        return None, txs


def check_address_transaction_ids_blockchain(address):
    if not address or not address.address:
        return None, []
    currency = address.currency

    return get_address_transaction_ids_blockchain(currency.code,
                                                  address.address)


loggers = {}


def get_nexchange_logger(name, with_console=True, with_email=False):

    global loggers

    if name in loggers:
        return loggers[name]
    else:
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
            print(get_traceback())

        loggers.update({'{}'.format(name): logger})

        return logger


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AESCipher:

    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')  # noqa

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)  # noqa

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]


class LogEmailBackend(EmailBackend):

    def __init__(self, *args, **kwargs):
        super(LogEmailBackend, self).__init__(
            *args, **kwargs, host=settings.LOG_EMAIL_HOST,
            port=settings.LOG_EMAIL_PORT,
            username=settings.LOG_EMAIL_USER,
            password=settings.LOG_EMAIL_PASSWORD
        )


class LogEmailHandler(AdminEmailHandler):
    def __init__(self):
        super(LogEmailHandler, self).__init__(
            email_backend='nexchange.utils.LogEmailBackend')


def ip_in_iplist(ip, ip_list):
    if ip in ip_list:
        return True
    ranges = [_ip for _ip in ip_list if '-' in _ip]
    for range in ranges:
        split_res = range.split('-')
        ip_range = IpRange(split_res[0], split_res[1])
        if ip in ip_range:
            return True
    return False


def convert_camel_to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
