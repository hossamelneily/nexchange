from django.core.urlresolvers import reverse
from django.conf import settings
import os
from collections import defaultdict
from django.db.models.signals import *


def data_provider(fn_data_provider):
    """
    Data provider decorator
    allows another callable to provide the data for the tests
    """
    def test_decorator(fn):
        def repl(self):
            for i in fn_data_provider():
                try:
                    fn(self, *i)
                except AssertionError as e:
                    print(i)
                    raise e
        return repl
    return test_decorator


def passive_authentication_helper(client,
                                  user,
                                  token,
                                  phone,
                                  is_logged_in):
    if not is_logged_in and user.is_authenticated():
        client.logout()
    # incorrect token
    response = client.post(
        reverse('accounts.verify_phone'), {'token': token,
                                           'phone': phone})

    return response


def get_ok_pay_mock(data='transaction_history'):
    mock_path = os.path.join(
        settings.BASE_DIR,
        'nexchange/tests/fixtures/'
        'okpay/{}.xml'.format(data)
    )
    with open(mock_path) as f:
        return str.encode(f.read().replace('\n', ''))


def get_payeer_pay_mock(data):
    mock_path = os.path.join(
        settings.BASE_DIR,
        'nexchange/tests/fixtures/'
        'payeer/{}.json'.format(data)
    )
    with open(mock_path) as f:
        return f.read().replace('\n', '')


def split_ok_pay_mock(mock, element):
    '''

    Args:
        mock: result from get_ok_pay_mock
        element: element name from xml i.e.: Comment, Currency

    Returns: element value

    '''
    m = mock.decode('utf-8')
    res = m.split(element)[1].split('>')[1].split('<')[0]
    return res


class DisableSignals:
    def __init__(self, disabled_signals=None):
        self.stashed_signals = defaultdict(list)
        self.disabled_signals = disabled_signals or [
            pre_init, post_init,
            pre_save, post_save,
            pre_delete, post_delete,
            pre_migrate, post_migrate,
        ]

    def __enter__(self):
        for signal in self.disabled_signals:
            self.disconnect(signal)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for signal in list(self.stashed_signals.keys()):
            self.reconnect(signal)

    def __round__(self, num):
        return round(num)

    def disconnect(self, signal):
        self.stashed_signals[signal] = signal.receivers
        signal.receivers = []

    def reconnect(self, signal):
        signal.receivers = self.stashed_signals.get(signal, [])
        del self.stashed_signals[signal]
