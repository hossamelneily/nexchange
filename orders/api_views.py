from core.common.serializers import UserResourceViewSet
from orders.models import Order
from orders.serizalizers import OrderSerializer, CreateOrderSerializer
from rest_framework_extensions.mixins import (
    ReadOnlyCacheResponseAndETAGMixin
)


class OrderListViewSet(UserResourceViewSet, ReadOnlyCacheResponseAndETAGMixin):
    model_class = Order
    lookup_field = 'unique_reference'
    serializer_class = OrderSerializer

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer

        return super(OrderListViewSet, self).get_serializer_class()

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Order.objects.all()
        return super(OrderListViewSet, self).get_queryset()
