from orders.serializers import MetaFlatOrder, OrderSerializer
from core.common.serializers import PartialModelSerializer
from django.contrib.auth.models import User


class UserOrderSerializer(OrderSerializer):
    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields +\
                 ('status', 'payment_window',
                  'payment_deadline', 'pair',)


class UserSerializer(PartialModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email',)
