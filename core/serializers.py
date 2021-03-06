from rest_framework import serializers
from core.models import Pair, Currency, Address, Transaction


class CurrencySerializer(serializers.ModelSerializer):

    class Meta:
        model = Currency
        fields = ('code', 'name', 'min_confirmations', 'is_crypto',
                  'minimal_amount', 'maximal_amount',
                  'is_base_of_enabled_pair', 'is_quote_of_enabled_pair',
                  'has_enabled_pairs',
                  'is_base_of_enabled_pair_for_test',
                  'is_quote_of_enabled_pair_for_test',
                  'has_enabled_pairs_for_test',
                  'withdrawal_fee')


class SimpleCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ('code', 'name')


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
        fields = ('name', 'base', 'quote', 'fee_ask', 'fee_bid', 'disabled',
                  'test_mode')


class SimplePairSerializer(serializers.ModelSerializer):
    base = SimpleCurrencySerializer()
    quote = SimpleCurrencySerializer()

    class Meta:
        model = Pair
        fields = ('name', 'base', 'quote')


class NestedPairSerializer(serializers.ModelSerializer):
    base = CurrencySerializer(many=False, read_only=True)
    quote = CurrencySerializer(many=False, read_only=True)
    fee_ask = serializers.ReadOnlyField()
    fee_bid = serializers.ReadOnlyField()

    class Meta:
        model = Pair
        fields = ('name', 'base', 'quote', 'fee_ask', 'fee_bid',)


class MetaAddress:
    model = Address
    fields = ('type', 'name', 'address', 'currency_code',)


class AddressSerializer(serializers.ModelSerializer):
    currency_code = serializers.ReadOnlyField(source='currency.code')

    def __init__(self, *args, **kwargs):
        add_params = kwargs.pop('additional_params', {})
        for k, v in add_params.items():
            self.fields[k] = serializers.CharField(default=v, required=False,
                                                   allow_blank=True,
                                                   allow_null=True,
                                                   read_only=False)
        super(AddressSerializer, self).__init__(*args, **kwargs)

    class Meta(MetaAddress):
        fields = MetaAddress.fields
        read_only_fields = ('type',)


class AddressUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('name', 'address',)
        # to make PATCH update possible
        read_only_fields = ('address',)


class NestedReadOnlyAddressSerializer(AddressSerializer):

    class Meta(MetaAddress):
        fields = MetaAddress.fields
        read_only_fields = fields


class NestedSimpleAddressSerializer(AddressSerializer):

    class Meta(MetaAddress):
        read_only_fields = ('type',)
        extra_kwargs = {
            'address': {'validators': []},
        }


class NestedAddressSerializer(NestedSimpleAddressSerializer):
    def __init__(self, *args, **kwargs):
        self.fields['destination_tag'] = serializers.CharField(
            required=False,
            write_only=True,
            allow_blank=True,
            allow_null=True,
        )
        self.fields['payment_id'] = serializers.CharField(
            required=False,
            write_only=True,
            allow_blank=True,
            allow_null=True,
        )
        super(NestedAddressSerializer, self).__init__(*args, **kwargs)


class TransactionSerializer(serializers.ModelSerializer):

    currency = serializers.ReadOnlyField(source='currency.code')

    class Meta:
        model = Transaction
        fields = ('created_on', 'modified_on', 'type',
                  'address_to', 'tx_id', 'confirmations',
                  'amount', 'is_verified', 'is_completed',
                  'time', 'currency')
        read_only_fields = fields
