import json
from functools import wraps
from nexchange.utils import get_client_ip

import requests
from django.conf import settings
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


def get_google_response(request, captcha_rs):
    url = "https://www.google.com/recaptcha/api/siteverify"
    params = {
        'secret': settings.RECAPTCHA_SECRET_KEY,
        'response': captcha_rs,
        'remoteip': get_client_ip(request)
    }
    verify_rs = requests.post(url, data=params, verify=True)
    verify_rs = verify_rs.json()
    success = verify_rs.get("success", False)
    return success


def recaptcha_required(view_fn):
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if request.method == 'POST':
            data = request.POST
            captcha_rs = data.get('g_recaptcha_response')
            success = get_google_response(request, captcha_rs)
            if not success:
                context = {
                    'status': 'error',
                    'message': str(_('Invalid reCAPTCHA!'))
                }
                return HttpResponse(
                    json.dumps(context),
                    # Precondition required
                    status=428,
                    content_type='application/json'
                )
        return view_fn(request, *args, **kwargs)
    return wrapper
