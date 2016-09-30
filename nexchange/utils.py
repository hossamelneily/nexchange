from twilio.rest import TwilioRestClient
from django.conf import settings
from twilio.exceptions import TwilioException
from uphold import Uphold


api = Uphold(settings.UPHOLD_IS_TEST)
api.auth_basic(settings.UPHOLD_USER, settings.UPHOLD_PASS)


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
