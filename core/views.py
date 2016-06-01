# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.template.loader import get_template

from nexchange.settings import MAIN_BANK_ACCOUNT
from core.forms import DateSearchForm, CustomUserCreationForm,\
    UserForm, UserProfileForm, UpdateUserProfileForm
from core.models import Order, Currency, SmsToken, Profile
from django.db import transaction
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from twilio.rest import TwilioRestClient
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError

from django.utils.translation import ugettext_lazy as _
from .validators import validate_bc
from datetime import timedelta
from django.views.decorators.clickjacking import xframe_options_exempt

from nexchange.settings import KRAKEN_PRIVATE_URL_API, KRAKEN_API_KEY, KRAKEN_API_SIGN

import requests 
import time


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

    return HttpResponse(template.render({'form': form,
                                         'orders': orders,
                                         'action': my_action
                                         },
                                        request))


def add_order(request):
    template = get_template('core/order.html')

    if request.method == 'POST':
        template = get_template('core/result_order.html')
        user = request.user
        curr = request.POST.get("currency_from", "RUB")
        amount_cash = request.POST.get("amount-cash")
        amount_coin = request.POST.get("amount-coin")
        currency = Currency.objects.filter(code=curr)[0]

        order = Order(amount_cash=amount_cash, amount_btc=amount_coin,
                      currency=currency, user=user)
        order.save()
        uniq_ref = order.unique_reference
        pay_until = order.created_on + timedelta(minutes=order.payment_window)

        my_action = _("Result")

        return HttpResponse(template.render({'bank_account': MAIN_BANK_ACCOUNT,
                                             'unique_ref': uniq_ref,
                                             'action': my_action,
                                             'pay_until': pay_until,
                                             },
                                            request))
    else:
        pass

    currencies = Currency.objects.filter().exclude(code="BTC").order_by('code')

    select_currency_from = """<select name="currency_from"
        class="currency-select currency-from">"""
    select_currency_to = """<select name="currency_to"
        class="currency-select currency-to">"""

    for ch in currencies:
        select_currency_from += """<option value ="%s">%s</option>""" % (
            ch.code, ch.name)
    select_currency_to += """<option value ="%s">%s</option>""" % (
        'BTC', 'BTC')
    select_currency_from += """</select>"""
    select_currency_to += """</select>"""

    my_action = _("Add")

    return HttpResponse(template.render({'slt1': select_currency_from,
                                         'slt2': select_currency_to,
                                         'action': my_action},
                                        request))



def user_registration(request):
    template = 'core/user_registration.html'
    success_message = _(
        'Registration completed. Check your phone for SMS confirmation code.')
    error_message = _('Error during resgistration. <br>Details: (%s)')

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
                    message = _send_sms(user)
                    messages.success(request, success_message)

                user = authenticate(
                    username=user.username,
                    password=user_form.cleaned_data['password1'])
                login(request, user)

                return redirect(
                    reverse(
                        'core.user_profile',
                        args=[
                            user.username]))

            except Exception as e:
                msg = error_message % (e)
                messages.error(request, msg)

    else:
        user_form = CustomUserCreationForm()
        profile_form = UserProfileForm()

    return render(
        request, template, {
            'user_form': user_form, 'profile_form': profile_form})


@method_decorator(login_required, name='dispatch')
class UserUpdateView(SingleObjectMixin, View):
    model = User
    slug_field = 'username'

    def get_object(self, queryset=None):
        ''' Testa se tem permissão de editar '''
        obj = super(UserUpdateView, self).get_object()
        if not obj == self.request.user:
            raise PermissionDenied
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        user_form = UserForm(instance=self.object)
        profile_form = UpdateUserProfileForm(instance=self.object.profile)

        ctx = {
            'user_form': user_form,
            'profile_form': profile_form,
        }

        return render(request, 'core/user_profile.html', ctx,)

    def post(self, request):
        self.object = self.get_object()
        user_form = UserForm(request.POST, instance=self.object)
        profile_form = UpdateUserProfileForm(
            request.POST, instance=self.object.profile)
        success_message = _('Profile updated with success')

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(self.request, success_message)

            return redirect(
                reverse(
                    'core.user_profile',
                    args=[
                        self.object.username]))
        else:
            ctx = {
                'user_form': user_form,
                'profile_form': profile_form,
            }

            return render(request, 'core/user_profile.html', ctx,)


def _send_sms(user, token=None):
    if token is None:
        token = SmsToken.objects.filter(user=user).latest('id')

    msg = _("BTC Exchange code:") + ' %s' % token.sms_token
    phone_to = str(user.username)

    client = TwilioRestClient(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=msg, to=phone_to, from_=settings.TWILIO_PHONE_FROM)

    return message


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
    if sent_token == sms_token.sms_token:
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
    new_address = request.POST.get('value')

    if not order.user == request.user:
        return HttpResponseForbidden(
            _("You don't have permission to edit this order"))
    elif order.frozen:
        return HttpResponseForbidden(
            _("This order can not be edited because is frozen"))
    else:
        try:
            if new_address == '':
                # if user is 'cleaning' the value
                new_address = None
            else:
                # If a value was sent, let's validate it
                validate_bc(new_address)

            order.withdraw_address = new_address
            order.save()
            return JsonResponse({'status': 'OK'}, safe=False)
        except ValidationError as e:
            msg = e.messages[0]
            return JsonResponse({'status': 'ERR', 'msg': msg}, safe=False)


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


def k_trades_history(request):
    # Todo use django rest framework
    url = KRAKEN_PRIVATE_URL_API % "TradesHistory"
    headers = {"API-Key": KRAKEN_API_KEY,
               "API-Sign": KRAKEN_API_SIGN}
    print(headers)
    data = {"nonce": int(time.time())}
    res = requests.post(url, headers=headers, data=data)

    print(res.json())


def user_by_phone(request):
    phone = request.POST.get('phone')
    user, created = User.objects.get_or_create(username=phone)
    Profile.objects.get_or_create(user=user)
    token = SmsToken(user=user)
    token.save()
    _send_sms(user, token)
    return JsonResponse({'status': 'ok'})


def ajax_menu(request):
    return render(request, 'core/partials/menu.html')


def ajax_crumbs(request):
    return render(request, 'core/partials/breadcrumbs.html')

@xframe_options_exempt
def ajax_order(request):
    template = get_template('core/partials/success_order.html')

    print (request.GET)
    user = request.user
    curr = request.POST.get("currency_from", "RUB")
    amount_cash = request.POST.get("amount-cash")
    amount_coin = request.POST.get("amount-coin")
    currency = Currency.objects.filter(code=curr)[0]
    print ('#########',amount_cash,amount_coin,currency)

    order = Order(amount_cash=amount_cash, amount_btc=amount_coin,
                  currency=currency, user=user)
    order.save()
    uniq_ref = order.unique_reference
    pay_until = order.created_on + timedelta(minutes=order.payment_window)

    my_action = _("Result")

   
    return template.render({'bank_account': MAIN_BANK_ACCOUNT,
                                         'unique_ref': uniq_ref,
                                         'action': my_action,
                                         'pay_until': pay_until,
                                         },
                                        request)
#    else:
 #       return JsonResponse({'status': 'error', 'message':'Wrong Method'})

