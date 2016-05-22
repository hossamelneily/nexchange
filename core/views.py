# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Avg, Sum, Count, F
from django.template.loader import get_template
from decimal import Decimal

from nexchange.settings import MAIN_BANK_ACCOUNT

from .forms import *
from core.models import *
from django.views.generic.edit import FormView
# Create your views here.
import os

import dateutil.parser

from django.db import transaction
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from twilio.rest import TwilioRestClient
from django.conf import settings
from django.http import JsonResponse
import json

#from forms import *
# Create your views here.
# login_required(login_url ='/login/')


def main(request):
    # alido si la empresa esta creada,  debe estarlo
    template = get_template('core/index.html')

    messages = []

    return HttpResponse(template.render({'messages': messages},  request))

def index_order(request):
    form_class = DateSearchForm
    model = Order
    template = get_template('core/index_order.html')
    paginate_by = 10
    form = form_class(request.POST or None)
    logged = request.user.is_authenticated()
    kwargs={}
    if request.user.is_authenticated():
        kwargs={"user":request.user}
    else:
        kwargs={"user":0}

    if form.is_valid():
        my_date = form.cleaned_data['date']
        if my_date:
            order_list = model.objects.filter(created_on__date=my_date,
                                              user=request.user)
        else:
            order_list = model.objects.filter(user=request.user)
    else:
        order_list = model.objects.filter(user=request.user)
    # print order_list.query
    # print len(order_list)
    # Show 10 rows per page
    paginator = Paginator(order_list,  paginate_by)
    page = request.GET.get('page')

    try:
        orders = paginator.page(page)

    except PageNotAnInteger:
        orders = paginator.page(1)

    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    #print orders.object_list
    return HttpResponse(template.render({'form': form,
                                         'orders': orders,
                                         'action' : 'Orders Main'
                                          },
                                        request))

def add_order(request):
    messages = []
    template = get_template('core/order.html')

    if request.method == 'POST':
        # print request.POST
        template = get_template('core/result_order.html')
        user = request.user
        curr = request.POST.get("currency_from","RUB")
        amount_cash = request.POST.get("amount-cash")
        amount_coin = request.POST.get("amount-coin")
        currency = Currency.objects.filter(code=curr)[0]

        order = Order(amount_cash=amount_cash, amount_btc=amount_coin,
                      currency=currency, user=user)
        order.save()

        uniq_ref = order.unique_reference

        return HttpResponse(template.render({'bank_account':MAIN_BANK_ACCOUNT, 
                                             'unique_ref':uniq_ref,
                                             'action': 'Result'},
                                            request))
        #return HttpResponseRedirect('/order/')
    else:
        pass
    
    currencies = Currency.objects.filter().exclude(code="BTC").order_by('code')

    select_currency_from = """<select name="currency_from" class="currency currency-from">"""
    select_currency_to = """<select name="currency_to" class="currency currency-to">"""

    for ch in currencies:
        select_currency_from += """<option value ="%s">%s</option>""" % (ch.code, ch.name)
    select_currency_to += """<option value ="%s">%s</option>""" % ('BTC', 'BTC')
    select_currency_from += """</select>"""
    select_currency_to += """</select>"""

    
    return HttpResponse(template.render({'slt1':select_currency_from, 
                                         'slt2':select_currency_to,
                                         'action': 'Add'},
                                        request))

def user_registration(request):
    template = 'core/user_registration.html'
    success_message = u'Registration completed. Check your phone for SMS confirmation code.'
    error_message = u'Error during resgistration. <br>Details: (%s)'

    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic(using='default'):
                    user = user_form.save(commit=False)
                    user.username = profile_form.cleaned_data['phone']
                    user.save()
                    
                    profile_form = UserProfileForm(request.POST, instance=user.profile)                    
                    profile = profile_form.save(commit=False)
                    profile.disabled = True
                    profile.save()

                    # send SMS token
                    message = _send_sms(user)
                    
                    messages.success(request, success_message)

                # Authenticate user and redirect to "activation" page
                user = authenticate(username=user.username, password=user_form.cleaned_data['password1'])
                login(request, user)

                return redirect(reverse('core.user_profile', args=[user.username]))
                

            except Exception as e:
                msg = error_message % (e)
                messages.error(request, msg)

    else:
        user_form = CustomUserCreationForm()
        profile_form = UserProfileForm()        

    return render(request, template, {'user_form': user_form, 'profile_form': profile_form})


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
        
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user_form = UserForm(request.POST, instance=self.object)
        profile_form = UpdateUserProfileForm(request.POST, instance=self.object.profile)
        success_message = 'Profile updated with success'

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(self.request, success_message)
            
            return redirect(reverse('core.user_profile', args=[self.object.username]))
        else:
            ctx = {
                'user_form': user_form, 
                'profile_form': profile_form, 
            }            

            return render(request, 'core/user_profile.html', ctx,)


def user_logout(request):
    logout(request)
    messages.success(request, 'Session finished')
    return redirect(reverse('main'))


def _send_sms(user):
    msg = "BTC Exchange code: '%s'" % user.profile.sms_token    

    client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(body=msg, to=str(user.profile.phone), from_=settings.TWILIO_PHONE_FROM)

    return message


@login_required(login_url='/login_backend/')
def resend_sms(request):
    # Should we generate another token..?
    message = _send_sms(request.user)
    return JsonResponse({'message_sid': message.sid}, safe=False)


@login_required(login_url='/login_backend/')
def verify_phone(request):
    sent_token = request.POST.get('token')
    if sent_token == request.user.profile.sms_token:
        profile = request.user.profile
        profile.disabled = False
        profile.save()
        status = 'OK'
    else:
        status = 'NOT_MATCH'

    return JsonResponse({'status': status}, safe=False)
