from unittest.mock import MagicMock

from django.test import TestCase

from core.tests.base import data_provider


class DataProviderDecoratorTestCase(TestCase):

    def test_calls_fn_data_provider(self):
        func_that_provides_data = MagicMock(return_value='x')
        func_that_is_decorated = MagicMock()

        decorator = data_provider(func_that_provides_data)
        decorated = decorator(func_that_is_decorated)
        decorated(None)

        self.assertTrue(func_that_provides_data.called)

    def test_calls_decorated_func_with_data_provided(self):
        param = '123'
        expected_calls = [((None, '1'),), ((None, '2'),), ((None, '3'),)]

        func_that_provides_data = MagicMock(return_value=param)
        func_that_is_decorated = MagicMock()

        decorator = data_provider(func_that_provides_data)
        decorated = decorator(func_that_is_decorated)

        decorated(None)

        self.assertEqual(func_that_is_decorated.call_count, 3)
        self.assertEqual(func_that_is_decorated.call_args_list, expected_calls)

    def test_catches_assertionError_on_decorated(self):

        func_that_provides_data = MagicMock(return_value='1')
        func_that_is_decorated = MagicMock(
            side_effect=AssertionError('Boom!'))

        decorator = data_provider(func_that_provides_data)
        decorated = decorator(func_that_is_decorated)

        with self.assertRaises(AssertionError):
            decorated(None)
