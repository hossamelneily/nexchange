from django.core.exceptions import ValidationError
from django.test import TestCase

from core.validators import (validate_address, validate_eth, validate_btc,
                             validate_ltc)
from core.tests.utils import data_provider


class ValidateBCTestCase(TestCase):

    def setUp(self):
        self.ltc_address = 'LYUoUn9ATCxvkbtHseBJyVZMkLonx7agXA'
        self.btc_address = '1GR9k1GCxJnL3B5yryW8Kvz7JGf31n8AGi'
        self.eth_address = '0x8116546AaC209EB58c5B531011ec42DD28EdFb71'

    def test_validator_recognizes_bad_address(self):
        with self.assertRaises(ValidationError):
            '''valid chars but invalid address'''
            validate_address('1AGNa15ZQXAZUgFiqJ3i7Z2DPU2J6hW62i')

        with self.assertRaises(ValidationError):
            validate_address('invalid chars like l 0 o spaces...')

    @data_provider(lambda: (
        ('LYUoUn9ATCxvkbtHseBJyVZMkLonx7agXA', validate_ltc,
         [validate_btc, validate_eth]),
        ('1GR9k1GCxJnL3B5yryW8Kvz7JGf31n8AGi', validate_btc,
         [validate_ltc, validate_eth]),
        ('0x8116546AaC209EB58c5B531011ec42DD28EdFb71', validate_eth,
         [validate_ltc, validate_btc]),
    ))
    def test_validate_different_address(self, address, validator,
                                        fail_validators):
        self.assertEqual(None, validator(address))
        self.assertEqual(None, validate_address(address))
        for fail_validator in fail_validators:
            with self.assertRaises(ValidationError):
                fail_validator(address)
