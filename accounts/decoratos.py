import json
from functools import wraps

from django.http.response import HttpResponse
from django.utils.translation import gettext_lazy as _


def not_logged_in_required(view_fn):
    @wraps(view_fn)
    def _wrapped_fn(request, *args, **kwargs):
        if request.user.is_authenticated:
            context = {
                'status': 'error',
                'message': str(_('You are already logged in'))
            }

            return HttpResponse(
                json.dumps(context),
                status=403,
                content_type='application/json'
            )

        return view_fn(request, *args, **kwargs)

    return _wrapped_fn
