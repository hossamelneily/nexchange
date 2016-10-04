# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.template.loader import get_template

from core.forms import DateSearchForm, CustomUserCreationForm,\
    UserForm, UserProfileForm, UpdateUserProfileForm, ReferralTokenForm
from core.models import Order, Currency, SmsToken, Profile, Transaction,\
    Address, Payment, PaymentMethod, PaymentPreference
from django.db import transaction
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from twilio.rest import TwilioRestClient
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from django.utils.translation import ugettext_lazy as _
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt

from twilio.exceptions import TwilioException

from .validators import validate_bc

from .kraken_api import api
from django.utils import translation
from decimal import Decimal
from referrals.models import Referral, ReferralCode
from core.utils import geturl_robokassa, check_signature_robo


kraken = api.API()


def main(request):
    template = get_template('core/index.html')
    _messages = []
    return HttpResponse(template.render({'messages': _messages}, request))


def index_order(request):
    form_class = DateSearchForm
    model = Order
    template = get_template('core/index_order.html')
    paginate_by = 10
    form = form_class(request.POST or None)
    if request.user.is_authenticated():
        kwargs = {"user": request.user}
    else:
        kwargs = {"user": 0}
    kwargs = {"is_failed": 0}

    if form.is_valid():
        my_date = form.cleaned_data['date']
        if my_date:
            kwargs["created_on__date"] = my_date
            order_list = model.objects.filter(**kwargs)
        else:
            order_list = model.objects.filter(**kwargs)
    else:
        order_list = model.objects.filter(**kwargs)

    paginator = Paginator(order_list, paginate_by)
    page = request.GET.get('page')

    try:
        orders = paginator.page(page)

    except PageNotAnInteger:
        orders = paginator.page(1)

    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    my_action = _("Orders Main")

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
    template = get_template('core/order.html')

    if request.method == 'POST':
        # Not in use order is added via ajax
        template = get_template('core/result_order.html')
        user = request.user
        curr = request.POST.get("currency_from", "RUB")
        amount_coin = Decimal(request.POST.get("amount-coin"))
        currency = Currency.objects.filter(code=curr)[0]
        order = Order(amount_btc=amount_coin,
                      currency=currency, user=user)
        order.save()
        uniq_ref = order.unique_reference
        pay_until = order.created_on + timedelta(minutes=order.payment_window)

        my_action = _("Result")

        return HttpResponse(template.render(
            {
                'unique_ref': uniq_ref,
                'action': my_action,
                'pay_until': pay_until,
            },
            request))
    else:
        pass
    crypto_pairs = [{'code': 'BTC'}]
    currencies = Currency.objects.filter().exclude(code='BTC')
    currencies = sorted(currencies, key=lambda x: x.code != 'RUB')

    # TODO: this code is utestable shit, move to template
    select_currency_from = """<select name="currency_from"
        class="currency-select currency-from
        price_box_selectbox_cont_selectbox classic">"""
    select_currency_to = """<select name="currency_to"
        class="currency-select
         currency-to price_box_selectbox_cont_selectbox classic">"""
    select_currency_pair = """<select name="currency_pair"
        class="currency-select currency-pair chart_panel_selectbox classic">"""

    for ch in currencies:
        select_currency_from += """<option value="{}">{}</option>"""\
            .format(ch.code, ch.name)
        for cpair in crypto_pairs:
            fiat = ch.code
            crypto = cpair['code']

            val = "{}/{}".format(crypto, fiat)
            select_currency_pair +=\
                """<option value="{fiat}" data-fiat="{fiat}"
            data-crypto={crypto}>{val}</option>"""\
                .format(fiat=fiat, crypto=crypto, val=val)

    select_currency_to += """<option value="{val}">{val}</option>"""\
        .format(val='BTC')

    select_currency_from += """</select>"""
    select_currency_to += """</select>"""
    select_currency_pair += """</select>"""

    my_action = _("Add")

    context = {
        'select_pair': select_currency_pair,
        'select_from': select_currency_from,
        'select_to': select_currency_to,
        'graph_ranges': settings.GRAPH_HOUR_RANGES,
        'action': my_action,
    }

    return HttpResponse(template.render(context, request))


def user_registration(request):
    template = 'core/user_registration.html'
    success_message = _(
        'Registration completed. Check your phone for SMS confirmation code.')
    error_message = _('Error during registration. <br>Details: {}')

    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic(using='default'):
                    user = user_form.save(commit=False)
                    user.username = profile_form.cleaned_data['phone']
                    user.save()

                    profile_form = UserProfileForm(
                        request.POST, instance=user.profile)
                    profile = profile_form.save(commit=False)
                    profile.disabled = True
                    profile.save()
                    res = _send_sms(user)
                    assert res
                    messages.success(request, success_message)

                user = authenticate(
                    username=user.username,
                    password=user_form.cleaned_data['password1'])
                login(request, user)

                return redirect(reverse('core.user_profile'))

            except Exception as e:
                msg = error_message.format(e)
                messages.error(request, msg)

    else:
        user_form = CustomUserCreationForm()
        profile_form = UserProfileForm()

    return render(
        request, template, {
            'user_form': user_form, 'profile_form': profile_form})


@method_decorator(login_required, name='dispatch')
class UserUpdateView(View):

    def get(self, request):
        user_form = UserForm(
            instance=self.request.user)
        profile_form = UpdateUserProfileForm(
            instance=self.request.user.profile)
        referral_form = ReferralTokenForm(
            instance=self.request.user.referral_code.get())

        ctx = {
            'user_form': user_form,
            'profile_form': profile_form,
            'referral_form': referral_form
        }

        return render(request, 'core/user_profile.html', ctx,)

    def post(self, request):
        user_form = \
            UserForm(request.POST,
                     instance=self.request.user)
        profile_form = \
            UpdateUserProfileForm(request.POST,
                                  instance=self.request.user.profile)
        referral_form = \
            ReferralTokenForm(request.POST,
                              instance=self.request.user.referral_code.get())
        success_message = _('Profile updated with success')

        if user_form.is_valid() and \
                profile_form.is_valid():
            user_form.save()
            profile_form.save()
            # referral_form.save()
            messages.success(self.request, success_message)

            return redirect(reverse('core.user_profile'))
        else:
            ctx = {
                'user_form': user_form,
                'profile_form': profile_form,
                'referral_form': referral_form
            }

            return render(request, 'core/user_profile.html', ctx,)


def _send_sms(user, token=None):
    if token is None:
        token = SmsToken.objects.filter(user=user).latest('id')

    msg = _("BTC Exchange code:") + ' %s' % token.sms_token
    phone_to = str(user.username)

    try:
        client = TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=msg, to=phone_to, from_=settings.TWILIO_PHONE_FROM)
        return message
    except TwilioException as err:
        return err


def resend_sms(request):
    phone = request.POST.get('phone')
    if request.user.is_anonymous() and phone:
        user = User.objects.get(profile__phone=phone)
    else:
        user = request.user
    message = _send_sms(user)
    return JsonResponse({'message_sid': message.sid}, safe=False)


def verify_phone(request):
    sent_token = request.POST.get('token')
    phone = request.POST.get('phone')
    anonymous = request.user.is_anonymous()
    if anonymous and phone:
        user = User.objects.get(username=phone)
    else:
        user = request.user
    sms_token = SmsToken.objects.filter(user=user).latest('id')
    if sent_token == sms_token.sms_token and sms_token.valid:
        profile = user.profile
        profile.disabled = False
        profile.save()
        status = 'OK'
        sms_token.delete()
        if anonymous:
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

    else:
        status = 'NO_MATCH'

    return JsonResponse({'status': status}, safe=False)


@login_required()
def update_withdraw_address(request, pk):
    order = Order.objects.get(pk=pk)
    address_id = request.POST.get('value')

    from_address = Address.objects.filter(
        user__username='onit', type='W').first()

    if not order.user == request.user:
        return HttpResponseForbidden(
            _("You don't have permission to edit this order"))
    elif order.frozen:
        return HttpResponseForbidden(
            _("This order can not be edited because is frozen"))

    if address_id:
        # be sure that user owns the address indicated
        try:
            a = Address.objects.get(
                user=request.user, pk=address_id)
        except ObjectDoesNotExist:
            return HttpResponseForbidden(
                _("Invalid addresses informed."))
    else:
        a = None

    if address_id == '':
        # if user is 'cleaning' the value
        # TODO: What to do here?
        order.transaction_set.all().delete()
    else:
        # TODO: Validate this behavior

        if order.has_withdraw_address:
            t = order.transaction_set.first()
        else:
            t = Transaction()
            t.order = order
            t.address_from = from_address

        t.address_to = a
        t.save()

    return JsonResponse({'status': 'OK'}, safe=False)


@login_required()
def create_withdraw_address(request):
    error_message = 'Error creating address: %s'

    address = request.POST.get('value')

    addr = Address()
    addr.type = Address.WITHDRAW
    addr.user = request.user
    addr.address = address

    try:
        validate_bc(addr.address)
        addr.save()
        resp = {'status': 'OK', 'pk': addr.pk}

    except ValidationError:
        resp = {'status': 'ERR', 'msg': 'The supplied address is invalid.'}

    except Exception as e:
        msg = error_message % (e)
        resp = {'status': 'ERR', 'msg': msg}

    return JsonResponse(resp, safe=False)


@login_required()
def payment_confirmation(request, pk):
    order = Order.objects.get(pk=pk)
    paid = (request.POST.get('paid') == 'true')

    if not order.user == request.user:
        return HttpResponseForbidden(
            _("You don't have permission to edit this order"))
    elif order.frozen:
        return HttpResponseForbidden(
            _("This order can not be edited because is frozen"))
    elif paid is True and not order.has_withdraw_address:
        return HttpResponseForbidden(
            _("An order can not be set as paid without a withdraw address"))
    else:
        try:
            order.is_paid = paid
            order.save()
            return JsonResponse({'status': 'OK',
                                 'frozen': order.frozen,
                                 'paid': order.is_paid}, safe=False)

        except ValidationError as e:
            msg = e.messages[0]
            return JsonResponse({'status': 'ERR', 'msg': msg}, safe=False)


@csrf_exempt
def user_by_phone(request):
    phone = request.POST.get('phone')
    user, created = User.objects.get_or_create(username=phone)
    Profile.objects.get_or_create(user=user)
    token = SmsToken(user=user)
    token.save()
    res = _send_sms(user, token)
    if isinstance(res, TwilioException):
        return JsonResponse({'status': 'error'})
    else:
        return JsonResponse({'status': 'ok'})


def ajax_menu(request):
    return render(request, 'core/partials/menu.html')


def ajax_crumbs(request):
    return render(request, 'core/partials/breadcrumbs.html')


@login_required
@csrf_exempt
def ajax_order(request):
    trade_type = int(request.POST.get("trade-type"))
    curr = request.POST.get("currency_from", "RUB")
    amount_coin = Decimal(request.POST.get("amount-coin"))
    currency = Currency.objects.filter(code=curr)[0]
    payment_method = request.POST.get("pp_type")
    identifier = request.POST.get("pp_identifier", None)
    identifier = identifier.replace(" ", "")

    amount_coin = Decimal(amount_coin)
    template = 'core/partials/modals/order_success_{}.html'.\
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

    my_action = _("Result")
    address = ""
    if trade_type == Order.SELL:
        address = k_generate_address()

    url = ''

    if payment_method == 'Robokassa':
        url = geturl_robokassa(order.id,
                               str(round(Decimal(order.amount_cash), 2)))

    return HttpResponse(template.render({'order': order,
                                         'unique_ref': uniq_ref,
                                         'action': my_action,
                                         'pay_until': pay_until,
                                         'address': address,
                                         'payment_method': payment_method,
                                         'url': url,
                                         },
                                        request))


def payment_methods_ajax(request):

    template = get_template('core/partials/payment_methods.html')

    payment_methods = PaymentMethod.objects.all()
    return HttpResponse(template.render({'payment_methods': payment_methods
                                         }, request))


def payment_methods_account_ajax(request):
    pm = request.GET.get("payment_method", None)
    template = get_template('core/partials/payment_methods_account.html')
    account = ''
    fee = ''

    if pm:
        payment_method = PaymentMethod.objects.get(pk=pm)
        account = payment_method.handler
        fee = payment_method.fee

    # print(payment_methods)
    return HttpResponse(template.render({'account': account,
                                         'fee': fee,
                                         }, request))


def user_address_ajax(request):
    user = request.user
    template = get_template('core/partials/user_address.html')
    addresses = Address.objects.filter(user=user, type="D")
    return HttpResponse(template.render({'addresses': addresses},
                                        request))


@csrf_exempt
def payment_ajax(request):
    template = get_template('core/partials/success_payment.html')
    curr = request.POST.get("currency_from", "RUB")
    amount_cash = request.POST.get("amount-cash")
    order_id = request.POST.get("order_id")
    currency = Currency.objects.filter(code=curr)[0]
    user = request.user
    order = Order.objects.get(pk=order_id)

    payment = Payment(amount_cash=amount_cash, currency=currency,
                      user=user, order=order)
    payment.save()
    uniq_ref = payment.unique_reference

    my_action = _("Result")

    return HttpResponse(template.render({'unique_ref': uniq_ref,
                                         'action': my_action,
                                         },
                                        request))


def k_generate_address():
    params = {
        'method': 'Bitcoin',
        'asset': 'XBT',
        'new': True
    }

    kraken_res = kraken.query_private('DepositAddresses', params)

    if kraken_res['error']:
        address = settings.MAIN_DEPOSIT_ADDRESSES[0]
    else:
        address = kraken_res['result'][0]['address']
    return address


def k_trades_history(request):
    # Todo use django rest framework
    k = kraken.query_private('TradesHistory')
    if k['error']:
        result = k['error']
    else:
        result = k['result']
    return JsonResponse({'result': result})


def k_deposit_status(request):
    params = {
        'method': 'Bitcoin',
        'asset': 'XBT',
    }

    k = kraken.query_private('DepositStatus', params)

    if k['error']:
        result = k['error']
    else:
        result = k['result']

    return JsonResponse({'result': result})


def user_btc_adress(request):
    btc_address = request.POST.get('btcAddress')
    user = request.user
    validate_bc(str(btc_address))
    address = Address(address=btc_address, user=user)
    address.save()
    return JsonResponse({'status': 'OK'})


def cards(request):
    def get_pref_by_name(name):
        curr_obj = Currency.objects.get(code=currency.upper())
        card = \
            PaymentPreference.\
            objects.filter(currency__in=[curr_obj],
                           user__is_staff=True,
                           payment_method__name__icontains=name)
        return card[0] if len(card) else 'None'

    template = get_template('core/partials/modals/payment_type.html')
    currency = request.POST.get("currency")

    cards = {
        'sber': get_pref_by_name('Sber'),
        'alfa': get_pref_by_name('Alfa'),
        'qiwi': get_pref_by_name('Qiwi'),
    }

    translation.activate(request.POST.get("_locale"))
    return HttpResponse(template.render({'cards': cards, 'type': 'buy'},
                                        request))


@csrf_exempt
def ajax_cards(request):
    def get_pref_by_name(name):
        curr_obj = Currency.objects.get(code=currency.upper())
        card = \
            PaymentPreference.\
            objects.filter(currency__in=[curr_obj],
                           user__is_staff=True,
                           payment_method__name__icontains=name)
        return card[0].identifier if len(card) else 'None'

    currency = request.POST.get("currency")

    cards = {
        'sber': get_pref_by_name('Sber'),
        'alfa': get_pref_by_name('Alfa'),
        'qiwi': get_pref_by_name('Qiwi'),
    }

    return JsonResponse({'cards': cards})


@login_required
def referrals(request):
    template = get_template('referrals/index_referrals.html')
    user = request.user
    referrals_code = ReferralCode.objects.filter(user=user).first()
    referrals_ = Referral.objects.filter(code=referrals_code)
    # return JsonResponse({'test': referrals_[0].turnover})

    paginate_by = 10
    model = Referral
    kwargs = {"code": referrals_code}
    referrals_list = model.objects.filter(**kwargs)
    paginator = Paginator(referrals_list, paginate_by)
    page = request.GET.get('page')

    try:
        referrals_list = paginator.page(page)

    except PageNotAnInteger:
        referrals_list = paginator.page(1)

    except EmptyPage:
        referrals_list = paginator.page(paginator.num_pages)

    return HttpResponse(template.render({'referrals': referrals_,
                                         'referrals_list': referrals_list},
                                        request))


@login_required
def payfailed(request):
    template = get_template('core/partials/steps/step_reply_payment.html')
    last_order = Order.objects.filter(user=request.user).latest('id')
    url = '/pay_try_again'
    last_order.is_failed = True
    last_order.save()
    return HttpResponse(template.render({'url_try_again': url}, request))


@login_required
def try_pay_again(request):
    old_order = Order.objects.filter(user=request.user,
                                     is_failed=True).latest('id')
    order = old_order
    order.id = None
    order.save()
    url = geturl_robokassa(order.id, str(order.amount_cash))
    return redirect(url)


@login_required
def paysuccess(request):
    try:
        out_summ = request.GET.get("OutSum")
        inv_id = request.GET.get("InvId")
        crc = request.GET.get("SignatureValue")
        check_res = check_signature_robo(inv_id, out_summ, crc)

        if not check_res:
            template = \
                get_template('core/partials/steps/step_reply_payment.html')
            return HttpResponse(template.render({'bad_sugnature': True},
                                                request))

        order = Order.objects.filter(user=request.user,
                                     amount_cash=out_summ,
                                     id=inv_id)[0]

        currency = Currency.objects.filter(code="RUB")[0]

        Payment.objects.\
            get_or_create(amount_cash=order.amount_cash,
                          currency=currency,
                          user=request.user,
                          payment_preference=order.payment_preference,
                          is_complete=False)

        return JsonResponse({'result': 'bad request'})
    except:
        return JsonResponse({'result': 'bad request'})
