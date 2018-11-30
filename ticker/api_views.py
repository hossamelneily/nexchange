from django.conf import settings

from core.common.api_views import DateFilterViewSet, DataPointsFilterViewSet
from ticker.models import Price
from ticker.serializers import PriceSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework_extensions.etag.mixins import (
    ReadOnlyETAGMixin
)
from rest_framework_extensions.cache.mixins import (
    CacheResponseMixin
)

from rest_framework import viewsets
from rest_framework_xml.parsers import XMLParser
from rest_framework_xml.renderers import XMLRenderer
from core.models import Market
from rest_framework.response import Response
from core.models import Pair
from decimal import Decimal
from orders.models import Order
from core.api_views import PairViewSet
from rest_framework.exceptions import NotFound


class BestChangeXMLRenderer(XMLRenderer):
    item_tag_name = "item"
    root_tag_name = "rates"


class BestChangeRateViewSet(viewsets.ModelViewSet):
    item_tag_name = 'list'
    root_tag_name = 'rates'
    queryset = Market.objects.all()
    parser_classes = (XMLParser,)
    renderer_classes = (BestChangeXMLRenderer,)
    http_method_names = ['get']

    def _get_order_return_data(self, order):
        pair = order.pair
        _from = pair.quote.code
        _min_from = order.get_amount_quote_min(user_format=True)
        _max_from = order.get_amount_quote_max(user_format=True)
        res = {
            'from': _from,
            'to': pair.base.code,
            'in': order.amount_quote,
            'out': order.amount_base,
            'amount': pair.base.available_reserves,
            'minamount': '{} {}'.format(_min_from, _from),
            'maxamount': '{} {}'.format(_max_from, _from),
        }
        if not pair.is_crypto:
            res.update({
                'from': 'CARD{}'.format(_from),
                'param': 'verifying'
            })
        return res

    def _get_bestchange_pair_names(self):
        pair_names = []
        currs = settings.BEST_CHANGE_CURRENCIES
        for i, base in enumerate(currs):
            for quote in currs[i + 1:]:
                pair_names.append(base + quote)
        return pair_names

    @method_decorator(cache_page(settings.PRICE_XML_CACHE_LIFETIME))
    def list(self, request):
        pair_view_set = PairViewSet()
        data = []
        pairs_names = self._get_bestchange_pair_names()
        pairs = Pair.objects.filter(disabled=False, test_mode=False,
                                    name__in=pairs_names)
        for pair in pairs:
            if not pair_view_set._get_dynamic_test_mode(pair):
                order = Order(pair=pair, amount_base=Decimal('1'))
                try:
                    order.calculate_quote_from_base()
                except Price.DoesNotExist:
                    continue
                data.append(self._get_order_return_data(order))
            reverse_pair = pair.reverse_pair
            if reverse_pair and not pair_view_set._get_dynamic_test_mode(
                    reverse_pair):
                order = Order(pair=reverse_pair, amount_quote=Decimal('1'))
                try:
                    order.calculate_base_from_quote()
                except Price.DoesNotExist:
                    continue
                data.append(self._get_order_return_data(order))
        return Response(data)


class LastPricesViewSet(ReadOnlyETAGMixin, CacheResponseMixin,
                        DateFilterViewSet):

    model_class = Price
    http_method_names = ['get']

    @method_decorator(cache_page(settings.PRICE_CACHE_LIFETIME))
    def dispatch(self, *args, **kwargs):
        return super(LastPricesViewSet, self).dispatch(*args, **kwargs)

    def list(self, request, pair=None):
        market_code = self.request.query_params.get('market_code', 'nex')
        if pair is not None:
            pair = pair.upper()
        queryset = Price.objects.filter(
            pair__name=pair, market__code=market_code
        ).order_by('-id')[:1]
        serializer = PriceSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, **kwargs):
        raise NotFound()


class PriceHistoryViewSet(ReadOnlyETAGMixin,
                          DataPointsFilterViewSet):
    serializer_class = PriceSerializer
    model_class = Price
    http_method_names = ['get']

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Price.objects
        if filters is None:
            filters = {}
        filters['pair__name'] = self.kwargs['pair'].upper()
        market_code = self.request.query_params.get('market_code', 'nex')
        filters['market__code'] = market_code
        res = super(PriceHistoryViewSet, self).get_queryset(filters=filters)

        return res

    def retrieve(self, request, **kwargs):
        raise NotFound()
