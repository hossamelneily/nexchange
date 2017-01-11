import json
from functools import wraps

import requests
from django.conf import settings
from django.http.response import HttpResponse, HttpResponseForbidden
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


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def recaptcha_required(view_fn):
    @wraps(view_fn)
    def wrapper(request, *args, **kwds):
        if request.method == 'POST':
            data = request.POST
            captcha_rs = data.get('g_recaptcha_response')
            verify = True
            if (captcha_rs == 'True') and settings.RECAPTCHA_ALLOW_DUMMY_TOKEN:
                verify = False
            url = "https://www.google.com/recaptcha/api/siteverify"
            params = {
                'secret': settings.RECAPTCHA_SECRET_KEY,
                'response': captcha_rs,
                'remoteip': _get_client_ip(request)
            }
            verify_rs = requests.post(url, data=params, verify=True)
            verify_rs = verify_rs.json()
            success = verify_rs.get("success", False)
            if not success and verify:
                return HttpResponseForbidden(_('Invalid reCAPTCHA!'))
        return view_fn(request, *args, **kwds)
    return wrapper
