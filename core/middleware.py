import pytz

from django.conf import settings
from datetime import datetime
from django.utils import timezone


class TimezoneMiddleware(object):
    def process_request(self, request):
        # TODO implement logout if TZ changes during session
        tzname = request.COOKIES.get('USER_TZ', settings.TIME_ZONE)
        try:
            timezone.activate(pytz.timezone(tzname))
        except Exception:
            timezone.deactivate()


class LastSeenMiddleware(object):
    def process_response(self, request, response):
        if hasattr(request, 'user') and \
                request.user and request.user.is_authenticated():
            profile = request.user.profile

            profile.last_visit_time = \
                datetime.now()
            profile.last_visit_ip = \
                request.META['REMOTE_ADDR']
            profile.save()
            # TODO: use naive time in db?
        return response
