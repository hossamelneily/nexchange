from rest_framework import serializers
from core.serializers import NestedAddressSerializer,\
    NestedReadOnlyAddressSerializer, NestedPairSerializer, \
    TransactionSerializer, SimplePairSerializer
from referrals.serializers import ReferralCodeSerializer
from ticker.serializers import RateSerializer

from orders.models import Order
from core.models import Address, Pair

from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as RestValidationError
from django.utils.translation import ugettext_lazy as _
from core.validators import get_validator, validate_xmr_payment_id, \
    validate_destination_tag


BASE_FIELDS = ('amount_base', 'is_default_rule', 'unique_reference',
               'amount_quote', 'pair', 'withdraw_address')
READABLE_FIELDS = ('deposit_address', 'created_on', 'from_default_rule',
                   'unique_reference', 'deposit_address',
                   'payment_window', 'payment_deadline', 'kyc_deadline',
                   'status_name', 'transactions', 'referral_code',
                   'withdrawal_fee', 'withdrawal_fee_quote',
                   'user_provided_amount')
RATE_FIELDS = ('amount_usd', 'amount_btc', 'amount_eur', 'price',
               'amount_quote_fee')
UPDATE_FIELDS = ('refund_address',)
CREATE_FIELDS = ('payment_url', 'token')
FIAT_FIELDS = ('payment_url',)
TOKEN_FIELDS = ('token',)
DETAIL_FIELDS = ('display_refund_address',)


class PrivateField(serializers.ReadOnlyField):

    def __init__(self, *args, **kwargs):
        self.default_public_return_value = kwargs.pop(
            'public_return_value', None
        )
        super(PrivateField, self).__init__(*args, **kwargs)

    def get_attribute(self, instance):
        """
        Given the *outgoing* object instance, return the primitive value
        that should be used for this field.
        """
        # Here < 2 is for listing sites that creates orders without payer
        # being logged in (such as conswitch)
        if instance.user.orders.all().count() < 2 \
                or instance.user == self.context['request'].user:
            return super(PrivateField, self).get_attribute(instance)
        return self.default_public_return_value


class MetaOrder:
    model = Order
    fields = BASE_FIELDS
    read_only_fields = READABLE_FIELDS


class MetaFlatOrder(MetaOrder):
    fields = MetaOrder.fields + READABLE_FIELDS


class OrderSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        super(OrderSerializer, self).__init__(*args, **kwargs)
        add_deposit_params = add_withdraw_params = {}
        if args and isinstance(self.instance, Order):
            order = self.instance
            add_deposit_params = {
                'destination_tag': order.quote_destination_tag,
                'payment_id': order.quote_payment_id
            }
            add_withdraw_params = {
                'destination_tag': order.base_destination_tag,
                'payment_id': order.base_payment_id
            }
        self.fields['deposit_address'] = NestedReadOnlyAddressSerializer(
            many=False, read_only=True,
            additional_params=add_deposit_params
        )
        self.fields['withdraw_address'] = NestedAddressSerializer(
            many=False, read_only=False, partial=True,
            additional_params=add_withdraw_params
        )

    referral_code = ReferralCodeSerializer(many=True, read_only=True,
                                           source='user.referral_code')
    pair = NestedPairSerializer(many=False, read_only=False)
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields


class OrderListSerializer(OrderSerializer):
    pair = SimplePairSerializer(many=False, read_only=False)


class OrderDetailSerializer(OrderSerializer):

    price = RateSerializer(many=False, read_only=True)
    payment_url = PrivateField(public_return_value=None)

    class Meta(MetaFlatOrder):
        fields = \
            MetaFlatOrder.fields + RATE_FIELDS + FIAT_FIELDS + DETAIL_FIELDS


class UpdateOrderSerializer(serializers.ModelSerializer):
    refund_address = NestedAddressSerializer(many=False,
                                             read_only=False, partial=True)

    class Meta(MetaOrder):
        fields = UPDATE_FIELDS

    def validate(self, data):
        if self.instance.refund_address:
            raise ValidationError(_(
                'Order {} already has refund address'.format(
                    self.instance.unique_reference
                )
            ))
        currency = self.instance.pair.quote.code
        validate_address = get_validator(currency)
        validate_address(data['refund_address']['address'])
        return super(UpdateOrderSerializer, self).validate(data)

    def update(self, instance, validated_data):
        refund_address = validated_data.pop('refund_address')
        addr_list = Address.objects.filter(address=refund_address['address'])
        if not addr_list:
            address = Address(**refund_address)
            address.type = Address.WITHDRAW
            address.currency = instance.pair.quote
            address.save()
        else:
            address = addr_list[0]
        instance.refund_address = address
        instance.save()
        return instance


class CreateOrderSerializer(OrderSerializer):
    class Meta(MetaOrder):
        # hack to allow seeing needed fields in
        # response from post (lines 47:51)
        fields = BASE_FIELDS + READABLE_FIELDS + FIAT_FIELDS + TOKEN_FIELDS

    def validate(self, data):
        # TODO: custom validation based on order.pair.base
        pair = data['pair']['name']
        try:
            pair_obj = Pair.objects.get(name=pair, disabled=False)
            self.pair = pair_obj
        except Pair.DoesNotExist:
            raise ValidationError(_('%(value)s is not'
                                    ' currently a supported Pair'),
                                  params={'value': pair})
        if all(['amount_base' not in data, 'amount_quote' not in data]):
            raise ValidationError(
                _('One of amount_quote and amount_base is required.'))

        currency = pair_obj.base.code
        validate_address = get_validator(currency)
        validate_address(data['withdraw_address']['address'])
        payment_id = data['withdraw_address'].get('payment_id', None)
        destination_tag = data['withdraw_address'].get('destination_tag', None)

        if payment_id not in ['', None]:
            if pair_obj.base.code != 'XMR':
                raise ValidationError('Payment id can\'t be '
                                      'used for {}'.format(self.pair.base))
            else:
                validate_xmr_payment_id(payment_id)
        if destination_tag not in ['', None]:
            if pair_obj.base.code != 'XRP':
                raise ValidationError('Destination tag can\'t be '
                                      'used for {}'.format(self.pair.base))
            else:
                validate_destination_tag(destination_tag)
        return super(CreateOrderSerializer, self).validate(data)

    def create(self, validated_data):
        for field in READABLE_FIELDS:
            validated_data.pop(field, None)
        withdraw_address = validated_data.pop('withdraw_address')
        payment_id = withdraw_address.pop('payment_id', None)
        destination_tag = withdraw_address.pop('destination_tag', None)
        validated_data.pop('pair')
        # Just making sure
        addr_list = Address.objects.filter(address=withdraw_address['address'])
        order = Order(pair=self.pair, **validated_data)
        if payment_id:
            order.payment_id = payment_id
        if destination_tag:
            order.destination_tag = destination_tag
        if not addr_list:
            address = Address(**withdraw_address)
            address.type = Address.WITHDRAW
            address.currency = order.pair.base
            address.save()
        else:
            address = addr_list[0]

        order.withdraw_address = address
        try:
            order.save()
            # get post_save stuff in sync
            order.refresh_from_db()
            self.fields['deposit_address'] = NestedReadOnlyAddressSerializer(
                many=False, read_only=True,
                additional_params={
                    'destination_tag': order.quote_destination_tag,
                    'payment_id': order.quote_payment_id
                }
            )
            self.fields['withdraw_address'] = NestedAddressSerializer(
                many=False, read_only=False,
                additional_params={
                    'destination_tag': order.base_destination_tag,
                    'payment_id': order.base_payment_id
                }
            )
            return order
        except ValidationError as e:
            raise RestValidationError({'non_field_errors': [e.message]})

    def update(self, instance, validated_data):
        # Forbid updating after creation
        return instance
