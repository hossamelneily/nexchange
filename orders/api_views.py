from django.conf import settings
from nexchange.permissions import NoUpdatePermission
from orders.models import Order
from orders.serizalizers import OrderSerializer, CreateOrderSerializer, \
    NestedPairSerializer
from accounts.utils import _create_anonymous_user
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework_extensions.mixins import (
    ReadOnlyCacheResponseAndETAGMixin
)
from rest_framework.response import Response
from collections import OrderedDict
from core.models import Currency, Pair
from django.db.models import Sum
from decimal import Decimal
from ticker.models import Ticker
from core.common.api_views import DateFilterViewSet
from referrals.middleware import ReferralMiddleWare

referral_middleware = ReferralMiddleWare()


class OrderPagination(PageNumberPagination):
    page_size = settings.RECENT_ORDERS_LENGTH
    page_size_query_param = 'page_size'


class OrderListViewSet(viewsets.ModelViewSet,
                       ReadOnlyCacheResponseAndETAGMixin):
    permission_classes = (NoUpdatePermission,)
    model_class = Order
    lookup_field = 'unique_reference'
    serializer_class = OrderSerializer
    pagination_class = OrderPagination

    @method_decorator(cache_page(settings.ORDER_CACHE_LIFETIME))
    def dispatch(self, *args, **kwargs):
        return super(OrderListViewSet, self).dispatch(*args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer

        return super(OrderListViewSet, self).get_serializer_class()

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Order.objects.all()
        return super(OrderListViewSet, self).get_queryset()

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            _create_anonymous_user(self.request)
            referral_middleware.process_request(self.request)
        serializer.save(user=self.request.user)

        return super(OrderListViewSet, self).perform_create(serializer)


class VolumeViewSet(ReadOnlyCacheResponseAndETAGMixin, DateFilterViewSet):

    model_class = Order

    def dispatch(self, *args, **kwargs):
        return super(VolumeViewSet, self).dispatch(*args, **kwargs)

    def get_queryset(self, filters=None, **kwargs):
        if filters is None:
            filters = {}
        filters['status'] = Order.COMPLETED
        return super(VolumeViewSet, self).get_queryset(filters=filters,
                                                       **kwargs)

    def get_rate(self, currency):
        BTC = Currency.objects.get(code='BTC')
        if currency == BTC:
            return Decimal('1')
        else:
            ticker = Ticker.objects.filter(
                pair__base=BTC, pair__quote=currency).last()
            return ticker.rate

    def list(self, request):
        params = self.request.query_params
        if 'hours' in params:
            hours = float(self.request.query_params.get('hours'))
        else:
            hours = 24
        queryset = self.get_queryset(hours=hours)
        data = OrderedDict({'hours': hours})
        volume_data = []
        pairs = Pair.objects.filter(disabled=False)
        total_base = total_quote = 0
        for pair in pairs:
            rate_base = self.get_rate(pair.base)
            rate_quote = self.get_rate(pair.quote)
            last_ask = Ticker.objects.filter(pair=pair).last().ask
            volume = queryset.filter(pair=pair).aggregate(
                Sum('amount_base'), Sum('amount_quote'))
            base_volume = volume['amount_base__sum']
            quote_volume = volume['amount_quote__sum']
            if base_volume is None:
                base_volume = Decimal('0.0')
            if quote_volume is None:
                quote_volume = Decimal('0.0')
            base_volume_btc = round(base_volume / rate_base, 8)
            quote_volume_btc = round(quote_volume / rate_quote, 8)
            total_base += base_volume_btc
            total_quote += quote_volume_btc
            pair_data = NestedPairSerializer(pair).data
            pair_data = OrderedDict({
                'base_volume': base_volume,
                'quote_volume': quote_volume,
                'base_volume_btc': base_volume_btc,
                'quote_volume_btc': quote_volume_btc,
                'last_ask': last_ask,
                'pair': pair_data
            })
            volume_data.append(pair_data)
        data.update({
            'total_volume': {
                'base_volume_btc': total_base,
                'quote_volume_btc': total_quote,
            }})
        data.update({'tradable_pairs': volume_data})

        data = OrderedDict(data)
        return Response(data)
