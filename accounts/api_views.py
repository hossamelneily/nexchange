from orders.api_views import OrderListViewSet
from rest_framework.permissions import IsAuthenticated
from accounts.serializers import UserOrderSerializer
from orders.models import Order


class UserOrderListViewSet(OrderListViewSet):
    permission_classes = OrderListViewSet.permission_classes + (IsAuthenticated,)
    serializer_class = UserOrderSerializer

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Order.objects.filter(user=self.request.user)
        return super(OrderListViewSet, self).get_queryset()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return super(UserOrderListViewSet, self).get_serializer_class()
        return UserOrderSerializer
