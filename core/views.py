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

def add_order(request):
    messages = []
    template = get_template('core/order.html')
    if request.method == 'POST':
        
        # If the save was successful,  redirect to another page

        return HttpResponseRedirect('/order/')
    else:
        pass
    
    currencies = Currency.objects.all()

    select_currency_from = """<select name ="currency_from">"""
    select_currency_to = """<select name ="currency_to">"""

    for ch in currencies:
        select_currency_from += """<option value ="%s">%s</option>""" % (ch.code, ch.name)
        select_currency_to += """<option value ="%s">%s</option>""" % (ch.code, ch.name)
    select_currency_from += """</select>"""
    select_currency_to += """</select>"""

    
    return HttpResponse(template.render({'slt1':select_currency_from, 'slt2':select_currency_to,
                                         'action': 'Add'},
                                        request))