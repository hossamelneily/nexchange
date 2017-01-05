from unittest.mock import Mock

from django.test import TestCase

from core.context_processors import country_code, timezone_country


class TestContextCountryCode(TestCase):

    def setUp(self):
        self.request = Mock()
        self.request.COOKIES = {}

    def test_timezone_country(self):
        """Check if timezone_country dict is correct"""
        res = timezone_country()
        self.assertIsInstance(res, dict)
        self.assertEqual(res['Europe/Vilnius'], 'LT')

    def test_country_code(self):
        """ Check if country short code comes from timezone"""
        res = country_code(self.request)
        self.assertIsInstance(res, dict)
        input_timezones = ['Europe/Vilnius', 'Europe/London']
        expected_country_codes = ['LT', 'GB']
        for i, tz in enumerate(input_timezones):
            self.request.COOKIES['USER_TZ'] = tz
            res = country_code(self.request)
            self.assertEqual(res['COUNTRY_CODE'], expected_country_codes[i])
