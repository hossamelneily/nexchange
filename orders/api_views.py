from django.conf import settings
from nexchange.permissions import NoUpdatePermission
from orders.models import Order
from orders.serizalizers import OrderSerializer, CreateOrderSerializer
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
from core.models import Currency
from django.db.models import Sum
from decimal import Decimal
from ticker.models import Ticker
from core.common.api_views import DateFilterViewSet


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
        volume_data = OrderedDict({})
        currs = Currency.objects.all()
        bases = [curr for curr in currs if curr.is_base_of_enabled_pair]
        total = 0
        for base in bases:
            rate = self.get_rate(base)
            volume = queryset.filter(pair__base=base).aggregate(
                Sum('amount_base'))
            base_sum = volume['amount_base__sum']
            if base_sum is None:
                volume['amount_base__sum'] = base_sum = Decimal('0.0')
            volume['amount_base__sum__btc'] = btc_sum = round(
                base_sum / rate, 8)
            total += btc_sum
            volume_data.update({base.code: volume})
        volume_data.update({'total': {'amount_base__sum__btc': total}})
        data.update({'volume': volume_data})

        data = OrderedDict(data)
        return Response(data)
