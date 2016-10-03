from twilio.rest import TwilioRestClient
from django.conf import settings
from twilio.exceptions import TwilioException
from uphold import Uphold
from requests import get
from django.core.mail import send_mail


api = Uphold(settings.UPHOLD_IS_TEST)
api.auth_basic(settings.UPHOLD_USER, settings.UPHOLD_PASS)


def send_email(to, msg=None, subject='BTC'):
    send_mail(
        subject,
        msg,
        'from@example.com',
        [to],
        fail_silently=False,
    )


def send_sms(msg, phone):
    try:
        client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=msg, to=phone, from_=settings.TWILIO_PHONE_FROM)
        return message
    except TwilioException as err:
        return err


def release_payment(withdraw, amount, type_='BTC'):
    try:
        txn_id = api.prepare_txn(settings.UPHOLD_CARD_ID,
                                 withdraw, amount, type_)
        api.execute_txn(settings.UPHOLD_CARD_ID, txn_id)
        return txn_id
    except Exception as e:
        print(str(e))
        return


def checktransaction(txt_id):
    if txt_id is None:
        return False
    btc_blockr = 'http://btc.blockr.io/api/v1/tx/info/' + str(txt_id)
    info = get(btc_blockr)
    if info.status_code != 200:
        return False
    count_confs = int(info.json()['data']['confirmations'])
    if count_confs > 0:
        return True
    else:
        return False
