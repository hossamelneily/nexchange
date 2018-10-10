from django.core.exceptions import ValidationError
import requests
from nexchange.utils import get_nexchange_logger
from django.conf import settings
from requests.auth import HTTPBasicAuth


class Idenfy:

    def __init__(self, url='https://ivs.idenfy.com/api/{version}/{endpoint}',
                 version='v2', api_key='api_key', api_secret='api_key'):
        self.url = url
        self.version = version
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        self.auth = HTTPBasicAuth(api_key, api_secret)

    def _check_fields(self, mandatory_fields, **fields):
        for field in mandatory_fields:
            if field not in fields:
                raise ValidationError(
                    'Missing mandatory field {}'.format(field))

    def _request(self, endpoint, mandatory_fields, **kwargs):
        self._check_fields(mandatory_fields, **kwargs)
        url = self.url.format(version=self.version, endpoint=endpoint)
        res = requests.post(
            url, headers=self.headers, json=kwargs, auth=self.auth
        )
        return res

    def request_token(self, **kwargs):
        endpoint = 'token'
        mandatory_fields = ['clientId']
        return self._request(endpoint, mandatory_fields, **kwargs)

    def get_redirect_url(self, token):
        endpoint = 'redirect?authToken={}'.format(token)
        return self.url.format(version=self.version, endpoint=endpoint)


class IdenfyAPIClient:
    def __init__(self):
        self.logger = get_nexchange_logger(self.__class__.__name__, True, True)
        self.api = Idenfy(
            url=settings.IDENFY_URL,
            version=settings.IDENFY_VERSION,
            api_key=settings.IDENFY_API_KEY,
            api_secret=settings.IDENFY_API_SECRET
        )

    def get_token_for_order(self, order, first_name='', last_name=''):
        res = self.api.request_token(**{
            'clientId': order.unique_reference,
            'firstName': first_name,
            'lastName': last_name
        })
        if res.status_code != 201:
            self.logger.error(
                'Bad request_token status code: 201!={}, content: {}'.format(
                    res.status_code,
                    res.content
                )
            )
            return
        return res.json().get('authToken')

    def get_redirect_url(self, token):
        if token:
            return self.api.get_redirect_url(token)
