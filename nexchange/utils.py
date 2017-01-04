import sys
import traceback

from django.conf import settings
from django.core.mail import send_mail
from requests import get
from twilio.exceptions import TwilioException
from twilio.rest import TwilioRestClient

from uphold import Uphold

api = Uphold(settings.UPHOLD_IS_TEST)
api.auth_basic(settings.UPHOLD_USER, settings.UPHOLD_PASS)


def send_email(to, msg=None, subject='BTC'):
    send_mail(
        subject,
        msg,
        'noreply@nexchange.ru',
        [to],
        fail_silently=False,
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
    try:
        txn_id = api.prepare_txn(settings.UPHOLD_CARD_ID,
                                 withdraw, amount, type_)
        print(txn_id)
        res = api.execute_txn(settings.UPHOLD_CARD_ID, txn_id)
        print(res)
        return txn_id
    except Exception as e:
        print('error {}'.format(e))
        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)


def check_transaction_blockchain(tx):
    if not tx or not tx.tx_id:
        return False
    network = 'btc'
    if settings.DEBUG:
        network = 'tbtc'
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

    def new_btc_card(self):
        """
        Create a new card Bitcoin
        """
        
        fields = {
            'label': 'User card',
            'currency': 'BTC',
        }
        return self._post('/me/cards/', fields)
    
    def new_ltc_card(self):
        """
        Create a new card Litecoin
        """
        
        fields = {
            'label': 'User card',
            'currency': 'LTC',
        }
        return self._post('/me/cards/', fields)
    
    def new_eth_card(self):
        """
        Create a new card Ethereum
        """
        
        fields = {
            'label': 'User card',
            'currency': 'ETH',
        }
        return self._post('/me/cards/', fields)
