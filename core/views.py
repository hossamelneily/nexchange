# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import get_language


def main(request):
    local_currency = 'RUB' if get_language() == 'ru' else 'EUR'
    pair = 'BTC' + local_currency
    params = {
        'pair': pair,
    }
    url = reverse('orders.add_order', kwargs=params)

    return HttpResponseRedirect(url)


def ajax_menu(request):
    return render(request, 'core/partials/menu.html')


def ajax_crumbs(request):
    return render(request, 'core/partials/breadcrumbs.html')
