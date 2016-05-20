# -*- coding: utf-8 -*-

from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Avg, Sum, Count, F
from django.template.loader import get_template
from decimal import Decimal

from nexchange.settings import MAIN_BANK_ACCOUNT
from forms import *
from core.models import *
# Create your views here.
import os

import dateutil.parser

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

    if form.is_valid():
        my_date = form.cleaned_data['date']
        if my_date:
            order_list = model.objects.filter(created_on__date=my_date)
        else:
            order_list = model.objects.all()
    else:
        order_list = model.objects.all()
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