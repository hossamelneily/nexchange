from rest_framework import serializers
from core.models import Pair, Currency


class PairSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pair
        fields = ('base', 'qoute')


class NestedPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pair
        fields = ('base', 'qoute')


# todo: change to ReadOnlyViewSet
class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ('code', 'name', 'min_confirmations', 'is_crypto',
                  'minimal_amount',
                  'is_base_of_enabled_pair', 'is_quote_of_enabled_pair',
                  'has_enabled_pairs')
