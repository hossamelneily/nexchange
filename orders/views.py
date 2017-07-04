from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import activate
from django.views.decorators.csrf import csrf_exempt
from core.common.forms import DateSearchForm
from core.models import Address, Pair
from core.views import main
from orders.models import Order
from payments.models import PaymentPreference, PaymentMethod, Payment
from payments.utils import geturl_robokassa, get_payeer_sign, get_payeer_desc
from nexchange.utils import send_email
from orders.task_summary import buy_order_release_by_reference_invoke, \
    buy_order_release_by_wallet_invoke, exchange_order_release_invoke
from accounts.task_summary import (import_transaction_deposit_crypto_invoke,
                                   update_pending_transactions_invoke)


@login_required
def orders_list(request):
    form_class = DateSearchForm
    model = Order
    template = get_template('orders/orders_list.html')
    paginate_by = 10
    form = form_class(request.POST or None)
    kwargs = {}
    if request.user.is_authenticated():
        kwargs['user'] = request.user

    if form.is_valid():
        my_date = form.cleaned_data['date']
        if my_date:
            kwargs['created_on__date'] = my_date

    order_list = model.objects.filter(**kwargs).exclude(
        status__in=[Order.CANCELED])

    order_list = [o for o in order_list if not o.expired]
    paginator = Paginator(order_list, paginate_by)
    page = request.GET.get('page')
    try:
        orders = paginator.page(page)

    except PageNotAnInteger:
        orders = paginator.page(1)

    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    my_action = _('Orders Main')

    addresses = []
    if not request.user.is_anonymous():
        addresses = request.user.address_set.filter(type=Address.WITHDRAW)

    return HttpResponse(template.render({'form': form,
                                         'orders': orders,
                                         'action': my_action,
                                         'withdraw_addresses': addresses,
                                         },
                                        request))


def add_order(request, pair=None):
    template = get_template('orders/order.html')
    if not pair:
        return main(request)
    if request.method == 'POST':
        # Not in use order is added via ajax
        template = \
            get_template('orders/partials/result_order.html')
        user = request.user
        amount_base = Decimal(request.POST.get('amount-coin'))
        _pair = Pair.objects.get(name=pair)
        order = Order(amount_base=amount_base,
                      pair=_pair, user=user)
        order.save()
        uniq_ref = order.unique_reference
        pay_until = order.created_on + timedelta(minutes=order.payment_window)

        my_action = _('Result')
        context = {
            'unique_ref': uniq_ref,
            'action': my_action,
            'pay_until': pay_until,
        }
        return HttpResponse(
            template.render(context, request)
        )

    pairs = Pair.objects.filter(disabled=False)
    base_currencies = set(pair.base.code for pair in pairs)
    quote_currencies = set(pair.quote.code for pair in pairs)

    my_action = _('Add')

    context = {
        'graph_ranges': settings.GRAPH_HOUR_RANGES,
        'pairs': pairs,
        'base_currencies': base_currencies,
        'quote_currencies': quote_currencies,
        'action': my_action,
        'DEFAULT_HOUR_RANGE': settings.DEFAULT_HOUR_RANGE,
    }

    return HttpResponse(template.render(context, request))


@login_required
@csrf_exempt
def ajax_order(request):
    def serialize_pref(data, user, method):
        optional_fields_serializer = {
            'iban': 'identifier',
            'phone-number': 'identifier',
            'account-numer': 'identifier',
            'name': 'beneficiary',
            'owner': 'beneficiary',
            'bic': 'bic',
        }
        serialized = {}
        for request_key, object_key in optional_fields_serializer.items():
            if request_key in data:
                if object_key in serialized:
                    raise ValueError('Double attribute found'.format(
                        object_key
                    ))
                serialized.update({object_key: data[request_key]})

        serialized.update({'user': user, 'payment_method': method})

        return serialized

    def update_pref(pref, serialized_data):
        for key, value in serialized_data.items():
            setattr(pref, key, value)

    def get_or_create_preference(req_data, _currency, user):
        payment_method = req_data.get('method')
        if payment_method:
            method = PaymentMethod.objects.get(
                name__icontains=payment_method
            )
        else:
            # will be retrieved through GuessPaymentPreference
            method = None

        serialized_data = serialize_pref(req_data, user, method)
        pref, created = \
            PaymentPreference.objects.get_or_create(
                user=serialized_data['user'],
                payment_method=serialized_data['payment_method'],
                identifier=serialized_data['identifier']
            )

        update_pref(pref, serialized_data)
        pref.currency.add(_currency)
        pref.save()
        return pref

    trade_type = int(request.POST.get('trade-type', Order.BUY))
    currency_from = request.POST.get('currency_from', 'RUB')
    currency_to = request.POST.get('currency_to', 'BTC')
    pair_name = currency_to + currency_from
    amount_base = Decimal(request.POST.get('amount-base'))
    # FIXME: add bad disabled pair user erros
    pair = Pair.objects.get(name=pair_name, disabled=False)
    _currency_from = pair.quote
    _currency_to = pair.base

    # Only for buy order right now
    exchange = False
    if request.POST.get('payment_preference') == 'EXCHANGE':
        exchange = True
        payment_method = None
    else:
        payment_method = request.POST.get('payment_preference[method]')
    amount_base = Decimal(amount_base)
    template = 'orders/partials/modals/order_success_{}.html'.\
        format('buy' if trade_type else 'sell')
    template = get_template(template)
    if payment_method is not None:
        if trade_type == Order.SELL:
            payment_pref_data = {
                'owner': request.POST.get('payment_preference[owner]'),
                'iban': request.POST.get('payment_preference[iban]'),
                'method': request.POST.get('payment_preference[method]')
            }
            payment_pref = get_or_create_preference(
                payment_pref_data,
                _currency_from,
                request.user
            )

        else:
            payment_pref = PaymentPreference.objects.get(
                user__is_staff=True,
                currency__in=[_currency_from],
                payment_method__name__icontains=payment_method
            )
    else:
        payment_pref = None

    order = Order(amount_base=amount_base,
                  order_type=trade_type, pair=pair, user=request.user,
                  exchange=exchange)
    if payment_pref is not None:
        order.payment_preference = payment_pref
    order.save()
    uniq_ref = order.unique_reference
    pay_until = order.created_on + timedelta(minutes=order.payment_window)
    activate(request.POST.get('_locale'))

    my_action = _('Result')
    address = ''
    if trade_type == Order.SELL:
        addresses = Address.objects.filter(
            user=request.user,
            currency=_currency_to,
            type=Address.DEPOSIT
        )
        address = addresses[0].address
    elif trade_type == Order.BUY and order.exchange:
        addresses = Address.objects.filter(
            user=request.user,
            currency=_currency_from,
            type=Address.DEPOSIT
        )
        address = addresses[0].address

    context = {
        'order': order,
        'amount_quote': order.amount_quote,
        'unique_ref': uniq_ref,
        'action': my_action,
        'pay_until': pay_until,
        'address': address,
        'payment_method': payment_method,
        'okpay_wallet': settings.OKPAY_WALLET

    }

    if payment_method == 'Robokassa':
        url = geturl_robokassa(order.id,
                               str(round(Decimal(order.amount_from), 2)))
        context.update({'url': url})
    elif payment_method == 'payeer':
        description = '{} {}BTC'.format(order.get_order_type_display(),
                                        order.amount_quote)
        desc = get_payeer_desc(description)
        ar_hash = (
            settings.PAYEER_WALLET,
            order.unique_reference,
            '%.2f' % order.amount_quote,
            order.pair.quote.code,
            desc,
            settings.PAYEER_IPN_KEY,
        )
        payeer_sign = get_payeer_sign(ar_hash=ar_hash)
        context.update({
            'payeer_sign': payeer_sign,
            'payeer_shop': settings.PAYEER_WALLET,
            'payeer_desc': desc
        })

    elif payment_method == 'okpay':
        context.update({'okpay_wallet': settings.OKPAY_WALLET})

    elif payment_method == 'sofort':
        context.update({
            'sofort_user_id': settings.SOFORT_USER_ID,
            'sofort_project_id': settings.SOFORT_PROJECT_ID
        })

    try:
        if not settings.DEBUG:
            send_email('oleg@onit.ws', 'NEW ORDER',
                       "{} {}".format(order, payment_pref))
    except:
        pass
    if trade_type == Order.SELL or order.exchange:
        import_transaction_deposit_crypto_invoke.apply_async(
            countdown=settings.TRANSACTION_IMPORT_TIME
        )
        curr = order.pair.base
        if trade_type == Order.BUY:
            curr = order.pair.quote

        countdown = curr.median_confirmation * 60

        update_pending_transactions_invoke.apply_async(
            countdown=countdown
        )

    res = template.render(context, request)
    return HttpResponse(res)


@login_required()
def update_withdraw_address(request, pk):
    order = Order.objects.get(pk=pk)
    address_id = request.POST.get('value')

    if not order.user == request.user:
        return HttpResponseForbidden(
            _('You don\'t have permission to edit this order'))
    elif order.withdrawal_address_frozen:
        return HttpResponseForbidden(
            _('This order can not be edited because it is already released'))
    if not order.user.profile.is_verified and not order.exchange:
        pm = order.payment_preference.payment_method
        if pm.required_verification_buy:
            return HttpResponseForbidden(
                _('You need to be a verified user to set withdrawal address '
                  'for order with payment method \'{}\'').format(pm.name))

    if address_id:
        # be sure that user owns the address indicated
        try:
            addr = Address.objects.get(
                user=request.user, pk=address_id)
            if order.order_type == Order.BUY:
                if addr.currency != order.pair.base:
                    return HttpResponseForbidden(
                        _('The currency({}) of this Address is not the same as'
                          ' the order base currency({}).'
                          ''.format(addr.currency.code, order.pair.base.code))
                    )
            else:
                if addr.currency != order.pair.quote:
                    return HttpResponseForbidden(
                        _('The currency({}) of this Address is not the same as'
                          ' the order quote currency({}).'
                          ''.format(addr.currency.code, order.pair.quote.code))
                    )
            new_withdraw_address = not order.withdraw_address
            addr.save()
            order.withdraw_address = addr
            order.save()
            if order.status == Order.PAID and new_withdraw_address:
                payment = order.payment_set.first()
                transaction = order.transactions.first()
                if transaction and order.exchange:
                    exchange_order_release_invoke.apply_async([
                        transaction.pk
                    ])
                    if order.order_type == order.BUY:
                        curr = order.pair.base
                    else:
                        curr = order.pair.quote
                    countdown = curr.median_confirmation * 60
                    update_pending_transactions_invoke.apply_async(
                        countdown=countdown)
                elif payment:
                    buy_order_release_by_reference_invoke.apply_async([
                        payment.pk
                    ])
                    countdown = order.pair.base.median_confirmation * 60
                    update_pending_transactions_invoke.apply_async(
                        countdown=countdown)
                else:
                    payments = Payment.objects.filter(user=request.user,
                                                      is_redeemed=False,
                                                      is_success=True)
                    for payment in payments:
                        buy_order_release_by_wallet_invoke\
                            .apply_async([payment.pk])

        except ObjectDoesNotExist:
            return HttpResponseForbidden(
                _('Invalid address provided'))

    return JsonResponse({'status': 'OK'}, safe=False)


def add_order_sell(request):
    return add_order(request)


@login_required()
def payment_confirmation(request, pk):
    order = Order.objects.get(pk=pk)
    paid = (request.POST.get('paid') == 'true')

    if not order.user == request.user:
        return HttpResponseForbidden(
            _('You don\'t have permission to edit this order'))
    elif order.payment_status_frozen:
        return HttpResponseForbidden(
            _('This order can not be edited because is it already released'))
    elif paid and not order.withdraw_address and order.is_buy \
            and not order.system_marked_as_paid:
        return HttpResponseForbidden(
            _('An order can not be set as paid without a withdraw address'))
    else:
        try:
            order.user_marked_as_paid = request.POST.get('paid') == 'true'
            order.save()

            return JsonResponse({'status': 'ok',
                                 'frozen': order.payment_status_frozen,
                                 'paid': order.user_marked_as_paid},
                                safe=False)

        except ValidationError as e:
            msg = e.messages[0]
            return JsonResponse({'status': 'ERR', 'msg': msg}, safe=False)
