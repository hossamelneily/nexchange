from django.conf import settings
from core.common.serializers import UserResourceViewSet
from orders.models import Order
from orders.serizalizers import OrderSerializer, CreateOrderSerializer
from accounts.utils import _create_anonymous_user
from rest_framework.pagination import PageNumberPagination
from rest_framework_extensions.mixins import (
    ReadOnlyCacheResponseAndETAGMixin
)


class OrderPagination(PageNumberPagination):
    page_size = settings.RECENT_ORDERS_LENGTH
    page_size_query_param = 'page_size'


class OrderListViewSet(UserResourceViewSet, ReadOnlyCacheResponseAndETAGMixin):
    model_class = Order
    lookup_field = 'unique_reference'
    serializer_class = OrderSerializer
    pagination_class = OrderPagination

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
