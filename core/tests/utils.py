from django.core.urlresolvers import reverse
from django.conf import settings
import os
from collections import defaultdict
from django.db.models.signals import *
from datetime import datetime
from time import time, sleep
from functools import wraps
from core.models import Pair

def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


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
        reverse('accounts.verify_user'), {'token': token,
                                          'phone': phone})

    return response


def get_mock(mock_path, output_type='bytes'):
    with open(mock_path) as f:
        s = f.read().replace('\n', '')
        if output_type == 'string':
            return s
        elif output_type == 'bytes':
            return str.encode(s)


def get_ok_pay_mock(data='transaction_history', output_type='bytes'):
    mock_path = os.path.join(
        settings.BASE_DIR,
        'nexchange/tests/fixtures/'
        'okpay/{}.xml'.format(data)
    )
    return get_mock(mock_path, output_type=output_type)


def create_ok_payment_mock_for_order(order, payment_id=None):
    if payment_id is None:
        payment_id = time()
    s = get_ok_pay_mock(data='transaction_history_empty', output_type='string')
    formatted = s.format(
        amount=order.amount_quote,
        email=order.payment_preference.identifier,
        receiver_wallet=settings.OKPAY_WALLET,
        unique_reference=order.unique_reference,
        currency=order.pair.quote.code,
        date=datetime.now().strftime('%Y-%M-%d %H:%M:%S'),
        payment_id=payment_id
    )
    return str.encode(formatted)


def get_payeer_mock(data, output_type='string'):
    mock_path = os.path.join(
        settings.BASE_DIR,
        'nexchange/tests/fixtures/'
        'payeer/{}.json'.format(data)
    )
    return get_mock(mock_path, output_type=output_type)


def create_payeer_mock_for_order(order):
    s = get_payeer_mock(data='transaction_history_empty', output_type='string')
    formatted = s.format(
        amount=order.amount_quote,
        receiver_wallet=settings.PAYEER_ACCOUNT,
        unique_reference=order.unique_reference,
        currency=order.pair.quote.code
    )
    return formatted


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


def read_fixture(path):
    full_path = os.path.join(settings.BASE_DIR, path)
    with open(full_path) as f:
        fixture = f.read()
    return fixture


def enable_all_pairs():
    pairs = Pair.objects.filter(disabled=True)
    for pair in pairs:
        pair.disabled = False
        pair.test_mode = False
        pair.disable_ticker = False
        pair.save()


def enable_prod_pairs():
    pairs = Pair.objects.filter(
        disabled=True,
        is_crypto=True,
        test_mode=False
    )
    for pair in pairs:
        pair.disabled = False
        pair.disable_ticker = False
        pair.save()
