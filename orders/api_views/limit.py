from .base import BaseOrderListViewSet
from orders.models import LimitOrder
from orders.serializers import LimitOrderSerializer, CreateLimitOrderSerializer


class LimitOrderListViewSet(BaseOrderListViewSet):
    model_class = LimitOrder
    serializer_class = LimitOrderSerializer

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateLimitOrderSerializer

        return super(LimitOrderListViewSet, self).get_serializer_class()
