from django.conf import settings
from rest_framework import viewsets
from nexchange.permissions import GetOnlyPermission
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page, never_cache
from core.models import Currency, Pair
from core.serializers import CurrencySerializer, PairSerializer
from rest_framework.response import Response
from random import randint


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

    def __init__(self, *args, **kwargs):
        super(PairViewSet, self).__init__(*args, **kwargs)
        self.base_test_mode_cache = {}
        self.quote_test_mode_cache = {}

    def _get_random_pair_queryset(self):
        queryset = Pair.objects.none()
        all_pairs = Pair.objects.filter(
            disabled=False, test_mode=False, disable_volume=False
        )
        if len(all_pairs) == 0:
            return queryset
        for i in range(1, 10):
            max_index = len(all_pairs) - 1
            random_index = randint(0, max_index)
            pair = all_pairs[random_index]
            if self._get_dynamic_test_mode(pair):
                continue
            else:
                return Pair.objects.filter(name=pair.name)
        return queryset

    def _get_query_by_name(self, name):
        if name == 'random':
            return self._get_random_pair_queryset()
        elif name == 'all':
            return self._get_all_pairs()
        else:
            return Pair.objects.filter(disable_volume=False, name=name.upper())

    def _get_all_pairs(self):
        return Pair.objects.filter(disable_volume=False)

    def get_queryset(self):
        name = self.request.query_params.get('name', None)
        if name:
            queryset = self._get_query_by_name(name)
        else:
            queryset = self._get_all_pairs()
        return queryset

    def dispatch(self, *args, **kwargs):
        return super(PairViewSet, self).dispatch(*args, **kwargs)

    def _get_dynamic_test_mode(self, pair):
        if pair.disabled or not pair.last_price_saved:
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

    @method_decorator(cache_page(settings.PAIR_CACHE_LIFETIME))
    def list(self, request, *args, **kwargs):
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

    @method_decorator(never_cache)
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        self.base_test_mode_cache = {}
        self.quote_test_mode_cache = {}
        pair_data = serializer.data
        if not pair_data['test_mode']:
            pair_data['test_mode'] = self._get_dynamic_test_mode(instance)
        return Response(pair_data)
