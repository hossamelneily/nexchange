import pytz

from django.utils import timezone
from django.conf import settings


class TimezoneMiddleware(object):

    def process_request(self, request):
        tzname = request.COOKIES.get('USER_TZ', settings.TIME_ZONE)
        try:
            timezone.activate(pytz.timezone(tzname))
        except Exception as e:
            timezone.deactivate()
