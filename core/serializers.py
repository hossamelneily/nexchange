from rest_framework import serializers
from core.models import Pair, Currency


# todo: change to ReadOnlyViewSet
class CurrencySerializer(serializers.ModelSerializer):

    class Meta:
        model = Currency
        fields = ('code', 'name', 'min_confirmations', 'is_crypto',
                  'minimal_amount',
                  'is_base_of_enabled_pair', 'is_quote_of_enabled_pair',
                  'has_enabled_pairs')


class CurrencyNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Currency
        fields = ('code',)

    def to_representation(self, instance):
        ret = super(CurrencyNameSerializer, self).to_representation(instance)
        return ret['code']


# todo: change to ReadOnlyViewSet
class PairSerializer(serializers.ModelSerializer):
    base = CurrencyNameSerializer()
    quote = CurrencyNameSerializer()

    class Meta:
        model = Pair
        fields = ('name', 'base', 'quote', 'fee_ask', 'fee_bid',)


class NestedPairSerializer(serializers.ModelSerializer):

    class Meta:
        model = Pair
        fields = ('name', 'base', 'quote', 'fee_ask', 'fee_bid',)
