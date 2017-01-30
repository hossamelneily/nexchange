from django.core.urlresolvers import reverse


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
    with open('nexchange/tests/fixtures/'
              'okpay/transaction_history.xml') as f:
        return str.encode(f.read().replace('\n', ''))
