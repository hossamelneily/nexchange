from rest_framework import viewsets
from orders.models import Order
from orders.serizalizers import OrderSerializer, CreateOrderSerializer
from rest_framework_extensions.mixins import (
    ReadOnlyCacheResponseAndETAGMixin
)
from nexchange.permissions import NoUpdatePermission, OwnerOnlyPermission


class OrderListViewSet(viewsets.ModelViewSet, ReadOnlyCacheResponseAndETAGMixin):
    serializer_class = OrderSerializer
    permission_classes = (NoUpdatePermission, OwnerOnlyPermission,)
    model_class = Order
    lookup_field = 'unique_reference'

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return OrderSerializer
        return CreateOrderSerializer

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Order.objects.all()
        return super(OrderListViewSet, self).get_queryset()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
