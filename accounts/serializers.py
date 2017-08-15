from orders.serizalizers import MetaFlatOrder, OrderSerializer
from accounts.models import Address
from rest_framework import serializers


class UserOrderSerializer(OrderSerializer):
    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields +\
                 ('status', 'payment_window',
                  'payment_deadline', 'pair')

