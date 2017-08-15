from rest_framework import serializers
from core.serializers import NestedAddressSerializer, NestedReadOnlyAddressSerializer
from orders.models import Order
from core.models import Address

BASE_FIELDS = ('amount_base', 'is_default_rule',
               'unique_reference', 'amount_quote', 'pair', 'withdraw_address')
READABLE_FIELDS = ('created_on', 'amount_quote', 'from_default_rule',
                   'unique_reference', 'order_type', 'deposit_address')


class MetaOrder:
    model = Order
    fields = BASE_FIELDS
    read_only_fields = READABLE_FIELDS


class MetaFlatOrder(MetaOrder):
    fields = MetaOrder.fields + READABLE_FIELDS


class OrderSerializer(serializers.ModelSerializer):
    pair_name = serializers.ReadOnlyField(source='pair.name')
    deposit_address = NestedReadOnlyAddressSerializer(many=False, read_only=True)
    withdraw_address = NestedAddressSerializer(many=False, read_only=False, partial=True)

    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields + ('pair_name',)


class CreateOrderSerializer(OrderSerializer):
    class Meta(MetaOrder):
        fields = MetaOrder.fields + ('pair',)
        read_only_fields = MetaOrder.read_only_fields + ('deposit_address',)

    def create(self, validated_data):
        withdraw_address = validated_data.pop('withdraw_address')
        # Just making sure
        addr_list = Address.objects.filter(address=withdraw_address['address'])
        order = Order(**validated_data)
        if not addr_list:
            address = Address(**withdraw_address)
            address.type = Address.WITHDRAW
            address.currency = order.pair.base
            address.save()
        else:
            address = addr_list[0]

        order.withdraw_address = address
        order.save()
        return order

    def update(self, instance, validated_data):
        # Forbid updating after creation
        return instance
