from django.conf import settings
from rest_framework import viewsets
from nexchange.permissions import GetOnlyPermission
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from core.models import Currency, Pair
from core.serializers import CurrencySerializer, PairSerializer
from rest_framework.response import Response


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
    queryset = Pair.objects.filter(disable_volume=False)
    lookup_field = 'name'
    http_method_names = ['get']

    def get_queryset(self):
        return Pair.objects.filter(disable_volume=False)

    def __init__(self, *args, **kwargs):
        super(PairViewSet, self).__init__(*args, **kwargs)
        self.base_test_mode_cache = {}
        self.quote_test_mode_cache = {}

    @method_decorator(cache_page(settings.PAIR_CACHE_LIFETIME))
    def dispatch(self, *args, **kwargs):
        return super(PairViewSet, self).dispatch(*args, **kwargs)

    def _get_dynamic_test_mode(self, pair):
        if pair.disabled:
            return True
        base_test_mode = self.base_test_mode_cache.get(pair.base.code, None)
        quote_test_mode = self.quote_test_mode_cache.get(pair.quote.code, None)
        if base_test_mode is None:
            base_test_mode = not pair.base.has_enough_reserves
            self.base_test_mode_cache.update({pair.base.code: base_test_mode})
        if quote_test_mode is None:
            quote_test_mode = pair.quote.has_too_much_reserves
            self.quote_test_mode_cache.update(
                {pair.quote.code: quote_test_mode}
            )
        return base_test_mode or quote_test_mode

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        self.base_test_mode_cache = {}
        self.quote_test_mode_cache = {}
        data = []
        for pair in queryset:
            pair_data = PairSerializer(pair).data
            if not pair_data['test_mode']:
                pair_data['test_mode'] = self._get_dynamic_test_mode(pair)
            data.append(pair_data)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        self.base_test_mode_cache = {}
        self.quote_test_mode_cache = {}
        pair_data = serializer.data
        if not pair_data['test_mode']:
            pair_data['test_mode'] = self._get_dynamic_test_mode(instance)
        return Response(pair_data)
