# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required

from django.core.urlresolvers import reverse
from django.http import (Http404, HttpResponse, JsonResponse,
                         HttpResponseForbidden, HttpResponseRedirect)
from django.shortcuts import redirect
from django.template.loader import get_template
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from nexchange.utils import get_nexchange_logger
from core.models import Currency
from orders.models import Order
from payments.adapters import (leupay_adapter, robokassa_adapter,
                               unitpay_adapter, okpay_adapter,
                               payeer_adapter)
from payments.models import Payment, PaymentPreference
from payments.utils import get_payeer_sign
from payments.task_summary import run_payeer, run_okpay
from decimal import Decimal


@login_required
def payment_failure(request):
    template = get_template('orders/partials/steps/step_retry_payment.html')
    # TODO: Better logic
    last_order = Order.objects.filter(user=request.user).latest('id')
    url = '/pay_try_again'
    last_order.status = Order.CANCELED
    last_order.save()
    return HttpResponse(template.render({'url_try_again': url}, request))


@login_required
def payment_retry(request):
    old_order = Order.objects.filter(user=request.user,
                                     status=Order.CANCELED).latest('id')
    order = old_order
    order.id = None
    order.save()
    url = '/'  # root
    # geturl_robokassa(order.id, str(order.amount_cash))
    return redirect(url)


def respond_retry(request):
    template = \
        get_template('orders/partials/steps/step_retry_payment.html')
    return HttpResponse(template.render({'bad_sugnature': True},
                                        request))


def payment_success(request, provider):
    logger = get_nexchange_logger(__name__)

    # TODO: this can be a decorator or middleware
    def flip_extension(host, resource, protocol='https',
                       query='redirect'):
        # solution with payeer working only for .co.uk
        site_name = host.split('.')[:1]
        full_host = '{}{}{}?{}=1'.format(
            site_name,
            '.co.uk' if host.endswith('.ru') else '.ru',
            resource,
            query
        )
        return '{}://{}'.format(protocol, full_host)

    if not request.user.is_authenticated():
        if 'redirect' not in request.GET:
            redirect_url = flip_extension(
                request.get_host(),
                request.path
            )
            logger.info('User is not authenticated '
                        'redirecting to {}'
                        .format(redirect_url))
            return HttpResponseRedirect(redirect_url)
        else:
            logger.info('User is still not authenticated '
                        'after redirect to {} request: {}'
                        .format(request.META['HTTP_HOST'],
                                request.__dict__))
    received_order = None
    if provider == 'robokassa':
        received_order = robokassa_adapter(request)
    elif provider == 'unitpay':
        received_order = unitpay_adapter(request)
    elif provider == 'leupay':
        received_order = leupay_adapter(request)
    elif provider == 'okpay':
        received_order = okpay_adapter(request)
    elif provider == 'payeer':
        received_order = payeer_adapter(request)

    # hacky hack
    supporterd = ['okpay', 'payeer']

    if provider not in supporterd:
        logger.error('Success view provider '
                     '{} not supported!'.format(provider))
    else:
        res = None
        if provider == 'payeer':
            res = run_payeer.apply()
        if provider == 'okpay':
            res = run_okpay.apply()
        logger.info('Triggered payeer payment import for {}'.format(provider))
        if res.state == 'SUCCESS':
            logger.info('SUCCESS import payments from success callback')
        else:
            logger.error('{} state import payments from success callback'
                         'traceback: {}'.format(res.state, res.traceback))

    logger.info('User at {} success view.'
                'request: {} user: {}'
                .format(provider,
                        request.__dict__,
                        request.user.__dict__))

    if not received_order:
        logger.error('Success view without a provider request: '
                     '{} not found!'.format(request.__dict__))
        return Http404(_('Unsupported payment provider'))

    lookup = {'user': request.user}
    if received_order.get('order_id'):
        lookup['unique_reference'] = \
            received_order['order_id']
    order = Order.objects.filter(**lookup).latest('id')

    if not order:
        logger.error('Success view provider request '
                     '{} not found!'.format(request.__dict__))
        return respond_retry(request)

    if not received_order.get('valid'):
        logger.error('Success view invalid payment request '
                     '{} not found!'.format(request.__dict__))
        return respond_retry(request)

    # This is only a provisional
    # flag which the user can set himself
    # does not affect business logic, only visual
    order.system_marked_as_paid = True
    order.save()

    # TODO: check signature
    # TODO: check api async for payment (optimization)
    redirect_url = "{}?oid={}&is_paid=true".\
        format(reverse('orders.orders_list'), order.unique_reference)
    logger.info('User at {} success view.'
                'request: {} user: {} redirected'
                'to order {}'
                .format(provider,
                        request.__dict__,
                        request.user.__dict__,
                        order.id))
    return redirect(redirect_url)


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
        'sepa': get_pref_by_name('SEPA', currency),
        'swift': get_pref_by_name('SWIFT', currency),
        'paypal': get_pref_by_name('PayPal', currency),
        'skrill': get_pref_by_name('Skrill', currency),
        'okpay': get_pref_by_name('Okpay', currency),
        'payeer': get_pref_by_name('Payeer', currency),
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
        'sepa': get_pref_by_name('SEPA', currency),
        'swift': get_pref_by_name('SWIFT', currency),
        'paypal': get_pref_by_name('PayPal', currency),
        'okpay': get_pref_by_name('Okpay', currency),

    }

    return JsonResponse({'cards': cards})


def payeer_status(request):
    if request.META['REMOTE_ADDR'] not in settings.PAYEER_IPS:
        return HttpResponseForbidden(_('IP address is not allowed.'))
    if not request.method == 'POST':
        return Http404(_('Resource not found'))
    retval = 'error'
    try:
        ar_hash = (
            request.POST['m_operation_id'],
            request.POST['m_operation_ps'],
            request.POST['m_operation_date'],
            request.POST['m_operation_pay_date'],
            request.POST['m_shop'],
            request.POST['m_orderid'],
            request.POST['m_amount'],
            request.POST['m_curr'],
            request.POST['m_desc'],
            request.POST['m_status'],
            settings.PAYEER_IPN_KEY
        )
        sign = get_payeer_sign(ar_hash=ar_hash)
        if (request.POST.get('m_sign') == sign and
                request.POST.get('m_status') == 'success'):
            retval = request.POST['m_orderid'] + '|success'

            o_list = Order.objects.filter(
                amount_quote=Decimal(request.POST['m_amount']),
                unique_reference=request.POST['m_orderid'],
                pair__quote__code=request.POST['m_curr']
            )
            if len(o_list) == 1:
                o = o_list[0]
                Payment.objects.get_or_create(
                    amount_cash=Decimal(request.POST['m_amount']),
                    user=o.user,
                    order=o,
                    reference=o.unique_reference,
                    payment_preference=o.payment_preference,
                    currency=o.pair.quote
                )
        else:
            retval = request.POST['m_orderid'] + '|error'
    except KeyError:
        pass
    return HttpResponse(retval)
