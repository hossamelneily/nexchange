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
from core.models import Address, Currency, Pair
from core.views import main
from orders.models import Order
from payments.models import PaymentPreference
from payments.utils import geturl_robokassa, get_payeer_sign, get_payeer_desc
from nexchange.utils import send_email


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
    else:
        pass
    pairs = Pair.objects.filter(disabled=False)
    base_currencies = set(pair.base.code for pair in pairs)

    my_action = _('Add')

    context = {
        'graph_ranges': settings.GRAPH_HOUR_RANGES,
        'pairs': pairs,
        'base_currencies': base_currencies,
        'action': my_action,
    }

    return HttpResponse(template.render(context, request))


@login_required
@csrf_exempt
def ajax_order(request):
    trade_type = int(request.POST.get('trade-type', Order.BUY))
    currency_from = request.POST.get('currency_from', 'RUB')
    currency_to = request.POST.get('currency_to', 'BTC')
    pair_name = currency_to + currency_from
    amount_base = Decimal(request.POST.get('amount-base'))
    pair = Pair.objects.get(name=pair_name)
    currency = Currency.objects.get(name=currency_from)
    payment_method = request.POST.get('pp_type')
    identifier = request.POST.get('pp_identifier', None)
    identifier = identifier.replace(' ', '')
    amount_base = Decimal(amount_base)
    template = 'orders/partials/modals/order_success_{}.html'.\
        format('buy' if trade_type else 'sell')
    template = get_template(template)

    if trade_type == Order.SELL:
        payment_pref, created = PaymentPreference.objects.get_or_create(
            identifier=identifier,
            user=request.user
        )
        payment_pref.currency.add(currency_to)
        payment_pref.save()
    else:
        payment_pref = PaymentPreference.objects.get(
            user__is_staff=True,
            currency__in=[currency],
            payment_method__name__icontains=payment_method
        )

    order = Order(amount_base=amount_base,
                  order_type=trade_type, payment_preference=payment_pref,
                  pair=pair, user=request.user)
    order.save()
    uniq_ref = order.unique_reference
    pay_until = order.created_on + timedelta(minutes=order.payment_window)
    activate(request.POST.get('_locale'))

    my_action = _('Result')
    address = ''
    if trade_type == Order.SELL:
        address = settings.MAIN_DEPOSIT_ADDRESSES.pop()

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

    try:
        send_email('oleg@onit.ws', 'NEW ORDER',
                   "{} {}".format(order, payment_pref))
    except:
        pass

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
            _('This order can not be edited because is frozen'))

    if address_id:
        # be sure that user owns the address indicated
        try:
            a = Address.objects.get(
                user=request.user, pk=address_id)
            a.save()
            order.withdraw_address = a
            order.save()
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
            _('This order can not be edited because is frozen'))
    elif paid is True and not order.withdraw_address:
        return HttpResponseForbidden(
            _('An order can not be set as paid without a withdraw address'))
    else:
        try:
            if order.status not in [Order.RELEASED, Order.COMPLETED]:
                # FIXME: change to flag 'customer_marked_as_paid' or smth
                order.status = Order.PAID
                order.save()
                send_email('oleg@onit.ws', '{} SET AS PAID',
                           "User: {} Order: {}".format(order.user, order))
            order_paid = (order.status >= Order.PAID)
            return JsonResponse({'status': 'ok',
                                 'frozen': order.payment_status_frozen,
                                 'paid': order_paid}, safe=False)

        except ValidationError as e:
            msg = e.messages[0]
            return JsonResponse({'status': 'ERR', 'msg': msg}, safe=False)
        except:
            pass
