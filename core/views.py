# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render


def main(request):
    url = reverse('referrals.main')

    return HttpResponseRedirect(url)


def ajax_menu(request):
    return render(request, 'core/partials/menu.html')


def ajax_crumbs(request):
    return render(request, 'core/partials/breadcrumbs.html')
