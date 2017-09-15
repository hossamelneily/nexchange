import json
from functools import wraps
from nexchange.utils import get_client_ip

import requests
from django.conf import settings
from django.http.response import HttpResponse
from django.utils.translation import gettext_lazy as _
from nexchange.api_clients.factory import ApiClientFactory
from core.models import AddressReserve


factory = ApiClientFactory()


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


def get_task(**kwargs):
    def _get_task(task_fn):
        @wraps(task_fn)
        def _wrapped_fn(search_val):
            Task = kwargs.get('task_cls')
            key = kwargs.get('key')
            lookup = {key: [search_val]}
            try:
                card = AddressReserve.objects.get(**lookup)
            except AddressReserve.DoesNotExist:
                return

            wallet = card.currency.wallet
            api = factory.get_api_client(wallet)
            task = Task(api, wallet=wallet)
            return task_fn(search_val, task)

        return _wrapped_fn
    return _get_task
