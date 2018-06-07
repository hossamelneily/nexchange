from django.core.exceptions import ValidationError

from core.validators import validate_address, validate_eth, validate_btc,\
    validate_ltc, get_validator, validate_bch
from core.tests.utils import data_provider
from core.models import Currency
from core.tests.base import OrderBaseTestCase


class ValidateBCTestCase(OrderBaseTestCase):

    def setUp(self):
        self.ltc_address = 'LYUoUn9ATCxvkbtHseBJyVZMkLonx7agXA'
        self.btc_address = '1GR9k1GCxJnL3B5yryW8Kvz7JGf31n8AGi'
        self.eth_address = '0x8116546AaC209EB58c5B531011ec42DD28EdFb71'
        self.bch_address = 'bitcoincash:qrlt24dt99gc9r7veal5rst8pc0m9zm3egadel8e6p'

    def tearDown(self):
        pass

    def test_validator_recognizes_bad_address(self):
        with self.assertRaises(ValidationError):
            '''valid chars but invalid address'''
            validate_address('1AGNa15ZQXAZUgFiqJ3i7Z2DPU2J6hW62i')

        with self.assertRaises(ValidationError):
            validate_address('invalid chars like l 0 o spaces...')

    @data_provider(lambda: (
        ('LYUoUn9ATCxvkbtHseBJyVZMkLonx7agXA', validate_ltc,
         [validate_btc, validate_eth, validate_bch]),
        ('1GR9k1GCxJnL3B5yryW8Kvz7JGf31n8AGi', validate_btc,
         [validate_ltc, validate_eth]),
        ('0x8116546AaC209EB58c5B531011ec42DD28EdFb71', validate_eth,
         [validate_ltc, validate_btc, validate_bch]),
        ('bitcoincash:qrlt24dt99gc9r7veal5rst8pc0m9zm3egadel8e6p', validate_bch,
         [validate_ltc, validate_btc, validate_eth]),
        ('35qL43qYwLdKtnR7yMfGNDvzv6WyZ8yT2n', validate_bch,
         [validate_ltc, validate_eth]),
    ))
    def test_validate_different_address(self, address, validator,
                                        fail_validators):
        self.assertEqual(None, validator(address))
        self.assertEqual(None, validate_address(address))
        for fail_validator in fail_validators:
            with self.assertRaises(ValidationError):
                fail_validator(address)

    def test_get_validator_for_all_crypto(self):
        cryptos = Currency.objects.filter(is_crypto=True)
        for crypto in cryptos:
            code = crypto.code
            res = get_validator(code)
            name = res.__name__
            self.assertNotEqual(
                name, 'validate_non_address',
                'Currency {} does not have a address validator'.format(code))
