import pytz
from django.conf import settings
from django.utils import timezone
from accounts.models import Profile


class TimezoneMiddleware(object):
    def __init__(self):
        super(TimezoneMiddleware, self).__init__()
        self.tzname = None

    def process_request(self, request):
        # TODO implement logout if TZ changes during session
        self.tzname = request.COOKIES.get('USER_TZ', settings.TIME_ZONE)
        try:
            timezone.activate(pytz.timezone(self.tzname))
        except Exception:
            timezone.deactivate()

    def process_response(self, request, response):
        if hasattr(request, 'user') and request.user.is_authenticated:
            Profile.objects.filter(pk=request.user.profile.pk)\
                .update(time_zone=self.tzname)

        return response


class LastSeenMiddleware(object):
    def process_response(self, request, response):
        if hasattr(request, 'user') and request.user.is_authenticated:
            Profile.objects.filter(pk=request.user.profile.pk)\
                .update(last_visit_time=timezone.now())

        return response
