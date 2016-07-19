from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils.translation import activate

from core.models import SmsToken


def data_provider(fn_data_provider):
    """
    Data provider decorator
    allows another callable to provide the data for the test
    """
    def test_decorator(fn):
        def repl(self):
            for i in fn_data_provider():
                try:
                    fn(self, *i)
                except AssertionError as e:
                    print("Assertion error caught with data set ", i)
                    raise e
        return repl
    return test_decorator


class UserBaseTestCase(TestCase):

    def setUp(self):
        self.username = '+555190909898'
        self.password = '123Mudar'
        self.data = \
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'johndoe@domain.com',
            }

        activate('en')

        self.user, created = User.objects.get_or_create(username=self.username)
        self.user.set_password(self.password)
        self.user.save()
        assert isinstance(self.user, User)
        token = SmsToken(user=self.user)
        token.save()
        self.client = Client()
        success = self.client.login(username=self.username,
                                    password=self.password)
        assert success
        super(UserBaseTestCase, self).setUpClass()
