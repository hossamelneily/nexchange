from payments.api_clients.base import BasePaymentApi
from django.conf import settings
import requests
import base64
import xmltodict


class SofortAPIClient(BasePaymentApi):

    def __init__(self, api_key=settings.SOFORT_API_KEY,
                 user_id=settings.SOFORT_USER_ID,
                 project_id=settings.SOFORT_PROJECT_ID,
                 url=settings.SOFORT_API_URL):
        super(SofortAPIClient, self).__init__()
        self.url = url
        self.project_id = project_id
        token = self._generate_token(user_id, api_key)

        self.headers = {
            'Authorization': 'Basic {}'.format(token),
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/xml; charset=UTF-8'
        }
        self.body_empty = '<?xml version="1.0" encoding="UTF-8"?>' \
                          '<transaction_request version="2">{}' \
                          '</transaction_request>'

    def _generate_token(self, user_id, api_key):
        bytes_token = base64.b64encode(
            bytes('{}:{}'.format(user_id, api_key), 'utf-8')
        )
        token = bytes_token.decode('utf-8')
        return token

    def _get_transaction_history(self, start_time=None):
        if start_time is None:
            body = self.body_empty.format('')
        else:
            body = self.body_empty.format(start_time)
        response = requests.post(self.url, data=body,
                                 headers=self.headers)
        return response

    def _validate_sofort_response(self, response):
        status = 1
        msg = 'OK'
        if response.status_code != 200:
            msg = 'Bad status code {} of Sofort transaction history ' \
                  'import. Check connection to Sofort!' \
                  ''.format(response.status_code)
            status = 0
            self.logger.error(msg)
        elif response.content == b'':
            msg = 'Empty response {} from Sofort. Check connection to ' \
                  'Sofort!'.format(response.content)
            status = 0
            self.logger.error(msg)
        return {'status': status, 'msg': msg}

    def get_transaction_history(self, start_time=None):
        trans_resp = self._get_transaction_history(start_time=start_time)
        valid_response = self._validate_sofort_response(trans_resp)
        if valid_response['status'] == 0:
            return {'error': valid_response['msg']}
        trans_dict = xmltodict.parse(trans_resp.content)
        if trans_dict['transactions'] is None:
            return {'transactions': []}
        transactions = trans_dict.get('transactions', {}).get(
            'transaction_details', []
        )
        if not isinstance(transactions, list):
            transactions = [transactions]
        res = {'transactions': transactions}
        return res
