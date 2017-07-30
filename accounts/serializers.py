from orders.serizalizers import MetaFlatOrder, OrderSerializer
from accounts.models import Address
from rest_framework import serializers


class UserOrderSerializer(OrderSerializer):
    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields +\
                 ('status', 'payment_window',
                  'payment_deadline', 'pair')


class MetaAddress:
    model = Address
    fields = ('type', 'currency', 'name', 'address',)


class AddressSerializer(serializers.ModelSerializer):
    currency_code = serializers.ReadOnlyField(source='currency.code')

    class Meta(MetaAddress):
        fields = MetaAddress.fields + ('currency_code',)


class AddressUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('name', 'address',)
        # to make PATCH update possible
        read_only_fields = ('address',)
