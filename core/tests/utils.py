from django.core.urlresolvers import reverse
from django.conf import settings
import os


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


def get_ok_pay_mock():
    mock_path = os.path.join(
        settings.BASE_DIR,
        'nexchange/tests/fixtures/'
        'okpay/transaction_history.xml'
    )
    with open(mock_path) as f:
        return str.encode(f.read().replace('\n', ''))
