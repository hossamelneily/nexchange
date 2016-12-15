from django.conf import settings
from orders.models import Order
from core.models import Currency, Address
from accounts.models import Profile
from payments.models import PaymentPreference
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from core.common.forms import DateSearchForm
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.exceptions import ObjectDoesNotExist
from datetime import timedelta
from decimal import Decimal
from django.utils.translation import activate, get_language,\
    ugettext_lazy as _
from payments.api_clients.braintree import BrainTreeAPI
from django.views.decorators.csrf import csrf_exempt
from payments.utils import geturl_robokassa
from django.core.exceptions import ValidationError


braintree_api = BrainTreeAPI()


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

    kwargs['is_failed'] = 0

    if form.is_valid():
        my_date = form.cleaned_data['date']
        if my_date:
            kwargs['created_on__date'] = my_date

    order_list = model.objects.filter(**kwargs)

    order_list = [o for o in order_list
                  if not o.expired and not o.is_completed]
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


def add_order(request):
    template = get_template('orders/order.html')

    if request.method == 'POST':
        # Not in use order is added via ajax
        template = \
            get_template('orders/partials/result_order.html')
        user = request.user
        curr = request.POST.get('currency_from', 'RUB')
        amount_coin = Decimal(request.POST.get('amount-coin'))
        currency = Currency.objects.filter(code=curr)[0]
        order = Order(amount_btc=amount_coin,
                      currency=currency, user=user)
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
            template.render(context, request))
    else:
        pass
    crypto_pairs = [{'code': 'BTC'}]
    local_currency = 'RUB' if get_language() == 'ru' else 'EUR'
    currencies = Currency.objects.filter().exclude(code='BTC')
    currencies = sorted(currencies,
                        key=lambda x: x.code != local_currency)

    # TODO: this code is utestable shit, move to template
    select_currency_from = '''<select name='currency_from'
        class='currency-select currency-from
        price_box_selectbox_cont_selectbox classic'>'''
    select_currency_to = '''<select name='currency_to'
        class='currency-select
         currency-to price_box_selectbox_cont_selectbox classic'>'''
    select_currency_pair = '''<select name='currency_pair'
        class='currency-select currency-pair chart_panel_selectbox classic'>'''

    for ch in currencies:
        select_currency_from += '''<option value='{}'>{}</option>'''\
            .format(ch.code, ch.name)
        for cpair in crypto_pairs:
            fiat = ch.code
            crypto = cpair['code']

            val = '{}/{}'.format(crypto, fiat)
            select_currency_pair +=\
                '''<option value='{fiat}' data-fiat='{fiat}'
            data-crypto={crypto}>{val}</option>'''\
                .format(fiat=fiat, crypto=crypto, val=val)

    select_currency_to += '''<option value='{val}'>{val}</option>'''\
        .format(val='BTC')

    select_currency_from += '''</select>'''
    select_currency_to += '''</select>'''
    select_currency_pair += '''</select>'''

    my_action = _('Add')

    context = {
        'select_pair': select_currency_pair,
        'select_from': select_currency_from,
        'select_to': select_currency_to,
        'graph_ranges': settings.GRAPH_HOUR_RANGES,
        'action': my_action,
    }

    return HttpResponse(template.render(context, request))


@login_required
@csrf_exempt
def ajax_order(request):
    trade_type = int(request.POST.get('trade-type', Order.BUY))
    curr = request.POST.get('currency_from', 'RUB')
    amount_coin = Decimal(request.POST.get('amount-coin'))
    currency = Currency.objects.filter(code=curr)[0]
    payment_method = request.POST.get('pp_type')
    identifier = request.POST.get('pp_identifier', None)
    identifier = identifier.replace(' ', '')
    amount_coin = Decimal(amount_coin)
    template = 'orders/partials/modals/order_success_{}.html'.\
        format('buy' if trade_type else 'sell')
    template = get_template(template)

    if trade_type == Order.SELL:
        payment_pref, created = PaymentPreference.objects.get_or_create(
            user=request.user,
            identifier=identifier
        )
        payment_pref.currency.add(currency)
        payment_pref.save()
    else:
        payment_pref = PaymentPreference.objects.get(
            user__is_staff=True,
            currency__in=[currency],
            payment_method__name__icontains=payment_method
        )

    order = Order(amount_btc=amount_coin,
                  order_type=trade_type, payment_preference=payment_pref,
                  currency=currency, user=request.user)
    order.save()
    uniq_ref = order.unique_reference
    pay_until = order.created_on + timedelta(minutes=order.payment_window)
    activate(request.POST.get('_locale'))

    my_action = _('Result')
    address = ''
    if trade_type == Order.SELL:
        address = settings.MAIN_DEPOSIT_ADDRESSES.pop()

    # url = '/orders'
    amount_cash = \
        str(round(Decimal(order.amount_cash), 2))

    context = {
        'order': order,
        'unique_ref': uniq_ref,
        'action': my_action,
        'pay_until': pay_until,
        'address': address,
        'payment_method': payment_method,
        'order_amount': amount_coin,
        'amount_cash': amount_cash,

    }
    if payment_method == 'Robokassa':
        url = geturl_robokassa(order.id,
                               str(round(Decimal(order.amount_cash), 2)))
        context.update({'url': url})

    elif payment_method == 'PayPal':
        profile = Profile.objects.get(user=request.user)
        template = 'orders/partials/modals/order_success_braintree.html'
        template = get_template(template)
        clienttoken = braintree_api.get_client_token(profile.sig_key)
        context.update({'client_token': clienttoken})

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
            assert a
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
    elif paid is True and not order.has_withdraw_address:
        return HttpResponseForbidden(
            _('An order can not be set as paid without a withdraw address'))
    else:
        try:
            order.is_paid = paid
            order.save()
            return JsonResponse({'status': 'OK',
                                 'frozen': order.payment_status_frozen,
                                 'paid': order.is_paid}, safe=False)

        except ValidationError as e:
            msg = e.messages[0]
            return JsonResponse({'status': 'ERR', 'msg': msg}, safe=False)
