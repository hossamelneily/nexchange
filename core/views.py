# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import get_language

from core.models import Pair


def main(request):
    local_currency = 'RUB' if get_language() == 'ru' else 'EUR'
    pair_name = 'BTC' + local_currency
    pairs = Pair.objects.filter(name=pair_name, disabled=False)
    if len(pairs) < 0:
        pair_name = Pair.objects.filter(disabled=False).first().name
    params = {
        'pair': pair_name,
    }
    url = reverse('orders.add_order', kwargs=params)

    return HttpResponseRedirect(url)


def ajax_menu(request):
    return render(request, 'core/partials/menu.html')


def ajax_crumbs(request):
    return render(request, 'core/partials/breadcrumbs.html')
