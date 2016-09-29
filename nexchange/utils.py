from twilio.rest import TwilioRestClient
from django.conf import settings
from twilio.exceptions import TwilioException
from core.kraken_api import api

kraken_api = api.API()


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


def withdraw(key, amount):
    params = {
        'asset': 'XBT',
        'key': key,
        'amount': amount
    }

    k = kraken_api.query_private('Withdraw', params)

    if k['error']:
        result = k['error']
    else:
        result = k['result']

    return result
