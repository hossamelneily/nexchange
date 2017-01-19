# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from core.models import Currency
from orders.models import Order
from payments.adapters import (leupay_adapter, robokassa_adapter,
                               unitpay_adapter, okpay_adapter)
from payments.models import Payment, PaymentPreference
from payments.utils import geturl_robokassa


@login_required
def payment_failure(request):
    template = get_template('orders/partials/steps/step_retry_payment.html')
    # TODO: Better logic
    last_order = Order.objects.filter(user=request.user).latest('id')
    url = '/pay_try_again'
    last_order.is_failed = True
    last_order.save()
    return HttpResponse(template.render({'url_try_again': url}, request))


@login_required
def payment_retry(request):
    old_order = Order.objects.filter(user=request.user,
                                     is_failed=True).latest('id')
    order = old_order
    order.id = None
    order.save()
    url = geturl_robokassa(order.id, str(order.amount_cash))
    return redirect(url)


@login_required
def payment_success(request, provider):
    try:
        received_order = None
        if provider == 'robokassa':
            received_order = robokassa_adapter(request)
        elif provider == 'unitpay':
            received_order = unitpay_adapter(request)
        elif provider == 'leupay':
            received_order = leupay_adapter(request)
        elif provider == 'okpay':
            received_order = okpay_adapter(request)

        if not received_order:
            return Http404(_('Unsupported payment provider'))

        if not received_order.valid:
            template = \
                get_template('orders/partials/steps/step_retry_payment.html')
            return HttpResponse(template.render({'bad_sugnature': True},
                                                request))

        order = Order.objects.filter(user=request.user,
                                     amount_cash=received_order['sum'],
                                     id=received_order['order_id'])[0]

        currency = order.currency.code

        Payment.objects.\
            get_or_create(amount_cash=order.amount_cash,
                          currency=currency,
                          user=request.user,
                          payment_preference=order.payment_preference,
                          is_complete=False)

        return redirect(reverse('orders.orders_list'))
    except ObjectDoesNotExist:
        return JsonResponse({'result': 'bad request'})


def payment_info(request, provider):
    assert provider
    pass


def payment_type(request):
    def get_pref_by_name(name, _currency):
        curr_obj = Currency.objects.get(code=_currency.upper())
        card = \
            PaymentPreference.\
            objects.filter(currency__in=[curr_obj],
                           user__is_staff=True,
                           payment_method__name__icontains=name)
        return card[0] if len(card) else 'None'

    template = get_template('payments/partials/modals/payment_type.html')
    currency = request.POST.get('currency')

    cards = {
        'sber': get_pref_by_name('Sber', currency),
        'alfa': get_pref_by_name('Alfa', currency),
        'qiwi': get_pref_by_name('Qiwi', currency),
        'paypal': get_pref_by_name('PayPal', currency),
        'skrill': get_pref_by_name('Skrill', currency),
        'okpay': get_pref_by_name('Okpay', currency),

    }
    local_vars = {
        'cards': cards,
        'type': 'buy',
        'currency': currency.upper(),
    }
    translation.activate(request.POST.get('_locale'))
    return HttpResponse(template.render(local_vars,
                                        request))


@csrf_exempt
def payment_type_json(request):
    def get_pref_by_name(name, _currency):
        curr_obj = Currency.objects.get(code=_currency.upper())
        card = \
            PaymentPreference.\
            objects.filter(currency__in=[curr_obj],
                           user__is_staff=True,
                           payment_method__name__icontains=name)
        return card[0].identifier if len(card) else 'None'

    currency = request.POST.get('currency')

    cards = {
        'sber': get_pref_by_name('Sber', currency),
        'alfa': get_pref_by_name('Alfa', currency),
        'qiwi': get_pref_by_name('Qiwi', currency),
        'paypal': get_pref_by_name('PayPal', currency),
        'okpay': get_pref_by_name('Okpay', currency),

    }

    return JsonResponse({'cards': cards})
