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
        form = ManageOrder(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.append('Succesfully saved !')
            # If the save was successful,  redirect to another page

            return HttpResponseRedirect('/order/')
    else:
        form = ""

    return HttpResponse(template.render({'form': form,
                                         'action': 'Add'},
                                        request))