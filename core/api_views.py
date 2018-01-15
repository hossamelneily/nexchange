from django.conf import settings
from rest_framework import viewsets
from nexchange.permissions import GetOnlyPermission
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from core.models import Currency, Pair
from core.serializers import CurrencySerializer, PairSerializer


class CurrencyViewSet(viewsets.ModelViewSet):

    permission_classes = (GetOnlyPermission,)
    serializer_class = CurrencySerializer
    queryset = Currency.objects.all()
    lookup_field = 'code'
    http_method_names = ['get']

    @method_decorator(cache_page(settings.CURRENCY_CACHE_LIFETIME))
    def dispatch(self, *args, **kwargs):
        return super(CurrencyViewSet, self).dispatch(*args, **kwargs)


class PairViewSet(viewsets.ModelViewSet):
    permission_classes = (GetOnlyPermission,)
    serializer_class = PairSerializer
    queryset = Pair.objects.all()
    lookup_field = 'name'
    http_method_names = ['get']

    @method_decorator(cache_page(settings.PAIR_CACHE_LIFETIME))
    def dispatch(self, *args, **kwargs):
        return super(PairViewSet, self).dispatch(*args, **kwargs)
