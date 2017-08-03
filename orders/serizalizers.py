from rest_framework import serializers
from core.serializers import NestedPairSerializer
from orders.models import Order

BASE_FIELDS = ('amount_base', 'is_default_rule',
               'unique_reference', 'amount_quote', 'pair',)
READABLE_FIELDS = ('created_on', 'amount_quote', 'from_default_rule',
                   'unique_reference', 'order_type')


class MetaOrder:
    model = Order
    fields = BASE_FIELDS
    read_only_fields = READABLE_FIELDS


class MetaFlatOrder(MetaOrder):
    fields = MetaOrder.fields + READABLE_FIELDS


class OrderSerializer(serializers.ModelSerializer):
    pair_name = serializers.ReadOnlyField(source='pair.name')

    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields + ('pair_name',)


class CreateOrderSerializer(OrderSerializer):

    class Meta(MetaOrder):
        fields = MetaOrder.fields + ('pair',)
