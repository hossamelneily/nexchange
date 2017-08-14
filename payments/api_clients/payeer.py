from payments.api_clients.base import BasePaymentApi
import requests
import json


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
        """ http://docs.payeercom.apiary.io/#reference/0/transferring-funds """

        payload = {
            'account': self.account,
            'apiId': self.apiId,
            'apiPass': self.apiPass,
            'action': 'transfer',
            'curIn': currency_in,
            'sum': amount,
            'curOut': currency_out,
            'comment': comment,
            'to': receiver
        }
        response = requests.post(self.url, payload)
        content = json.loads(response.content.decode('utf-8'))
        return content
