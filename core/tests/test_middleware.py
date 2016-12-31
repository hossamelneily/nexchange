from unittest.mock import Mock

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from core.middleware import TimezoneMiddleware


class TimezoneMiddlewareTestCase(TestCase):

    def setUp(self):
        self.middleware = TimezoneMiddleware()
        self.request = Mock()
        self.request.COOKIES = {}

    def test_process_request_without_tz_cookie(self):
        self.middleware.process_request(self.request)

        active_tz = timezone.get_current_timezone_name()

        self.assertEqual(active_tz, settings.TIME_ZONE)

    def test_process_request_with_tz_cookie(self):
        user_tz = 'Asia/Vladivostok'
        self.request.COOKIES = {'USER_TZ': user_tz}

        self.middleware.process_request(self.request)

        active_tz = timezone.get_current_timezone_name()
        self.assertEqual(active_tz, user_tz)

    def test_uses_settings_tz_for_invalid_cookie(self):
        # ensure starts with one that is not the one in settings.py
        initial_tz = 'Asia/Vladivostok'
        self.assertNotEqual(settings.TIME_ZONE, initial_tz)
        timezone.activate(initial_tz)

        # set a invalid TZ via cookie
        user_tz = 'Wonder/Land'
        self.request.COOKIES = {'USER_TZ': user_tz}
        self.middleware.process_request(self.request)

        active_tz = timezone.get_current_timezone_name()
        self.assertEqual(settings.TIME_ZONE, active_tz)
