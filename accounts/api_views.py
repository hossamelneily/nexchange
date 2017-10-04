from orders.api_views import OrderListViewSet
from rest_framework import permissions
from core.common.api_views import UserResourceViewSet
from core.common.viewsets import NoDeleteModelViewSet
from accounts.serializers import UserOrderSerializer, UserSerializer
from orders.models import Order
from core.models import Address
from core.serializers import AddressSerializer, AddressUpdateSerializer
import django_filters.rest_framework
# from nexchange.permissions import OwnerOnlyPermission
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated


class UserViewSet(NoDeleteModelViewSet):
    permission_classes = (IsAuthenticated,)
    model = User
    serializer_class = UserSerializer
    lookup_field = 'username'
    queryset = User.objects.all()

    def get_object(self):
        """
        Handle regular lookup, and /users/me/
        """
        lookup = self.kwargs.get(self.lookup_field)
        if lookup == 'me':
            lookup = self.request.user.username

        return self.queryset.get(username=lookup)

    def get_queryset(self):
        """Limit the queryset for listing only"""
        queryset = self.queryset.filter(**self.kwargs)

        if self.request.user.is_staff:
            return queryset

        return []


class UserOrderListViewSet(OrderListViewSet):
    permission_classes = OrderListViewSet.permission_classes + \
        (permissions.IsAuthenticated,)
    serializer_class = UserOrderSerializer

    def get_queryset(self, filters=None, **kwargs):
        self.queryset = Order.objects.filter(user=self.request.user)
        return super(OrderListViewSet, self).get_queryset()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return super(UserOrderListViewSet, self).get_serializer_class()
        return UserOrderSerializer


class UserAddressViewSet(UserResourceViewSet):
    permission_classes = UserResourceViewSet.permission_classes + \
        (permissions.IsAuthenticated,)
    filter_fields = ('type', 'currency')
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    model_class = Address
    serializer_class = AddressSerializer
    lookup_field = 'address'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AddressUpdateSerializer
        return super(UserAddressViewSet, self).get_serializer_class()

    def get_queryset(self):
        self.queryset = Address.objects.filter(user=self.request.user)
        return super(UserAddressViewSet, self).get_queryset()

    def filter_queryset(self, queryset):
        # super needs to be called to filter backends to be applied
        queryset = super().filter_queryset(queryset)
        return queryset

    def perform_create(self, serializer):
        # the user can only create WITHDRAW addresses, as deposit are internal
        serializer.save(user=self.request.user, type=Address.WITHDRAW)
        super(UserResourceViewSet, self).perform_create(serializer)
