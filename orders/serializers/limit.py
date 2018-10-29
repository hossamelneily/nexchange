from core.serializers import NestedSimpleAddressSerializer,\
    NestedReadOnlyAddressSerializer, NestedPairSerializer, \
    TransactionSerializer, SimplePairSerializer
from referrals.serializers import ReferralCodeSerializer

from orders.models import LimitOrder, OrderBook
from core.models import Address, Pair

from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as RestValidationError
from django.utils.translation import ugettext_lazy as _
from core.validators import get_validator
from .base import BaseOrderSerializer


BASE_FIELDS = (
    'pair', 'order_type', 'amount_base', 'unique_reference', 'limit_rate',
    'rate', 'amount_quote', 'withdraw_address', 'refund_address'
)
READABLE_FIELDS = (
    'status_name', 'book_status_name', 'rate', 'deposit_address', 'created_on',
    'unique_reference', 'transactions', 'referral_code',
)
UPDATE_FIELDS = ()
CREATE_FIELDS = ('token')
FIAT_FIELDS = ()
TOKEN_FIELDS = ('token',)


class MetaLimitOrder:
    model = LimitOrder
    fields = BASE_FIELDS
    read_only_fields = READABLE_FIELDS


class MetaFlatOrder(MetaLimitOrder):
    fields = MetaLimitOrder.fields + READABLE_FIELDS


class LimitOrderSerializer(BaseOrderSerializer):

    deposit_address = NestedReadOnlyAddressSerializer(
        many=False, read_only=True,
    )
    withdraw_address = NestedSimpleAddressSerializer(
        many=False, read_only=False, partial=True
    )
    refund_address = NestedSimpleAddressSerializer(
        many=False, read_only=False, partial=True
    )

    referral_code = ReferralCodeSerializer(many=True, read_only=True,
                                           source='user.referral_code')
    pair = NestedPairSerializer(many=False, read_only=False)
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields


class OrderListSerializer(LimitOrderSerializer):
    pair = SimplePairSerializer(many=False, read_only=False)


class OrderDetailSerializer(LimitOrderSerializer):

    class Meta(MetaFlatOrder):
        fields = MetaFlatOrder.fields + FIAT_FIELDS


class CreateLimitOrderSerializer(LimitOrderSerializer):
    deposit_address = NestedReadOnlyAddressSerializer(
        many=False, read_only=True,
    )

    class Meta(MetaLimitOrder):
        fields = BASE_FIELDS + READABLE_FIELDS + FIAT_FIELDS + TOKEN_FIELDS

    def __init__(self, *args, **kwargs):
        data = kwargs.get('data', None)
        if data:
            for key in ['amount_base', 'amount_quote', 'limit_rate']:
                data = self.strip_payload_decimal(data, key)
        super(CreateLimitOrderSerializer, self).__init__(*args, **kwargs)

    def _get_address_keys(self, data):
        order_type = data.get('order_type', LimitOrder.BUY)
        base_addr = 'withdraw' if order_type == LimitOrder.BUY else 'refund'
        quote_addr = 'refund' if order_type == LimitOrder.BUY else 'withdraw'
        return {
            'base_address': '{}_address'.format(base_addr),
            'quote_address': '{}_address'.format(quote_addr),
        }

    def validate(self, data):
        # TODO: custom validation based on order.pair.base
        pair = data['pair']['name']
        try:
            pair_obj = Pair.objects.get(name=pair, disabled=False)
            self.pair = pair_obj
            self.order_book = OrderBook.objects.get(
                pair=self.pair, disabled=False, flagged=False
            )
        except (Pair.DoesNotExist, OrderBook.DoesNotExist):
            raise ValidationError(_('%(value)s is not'
                                    ' currently a supported Pair'),
                                  params={'value': pair})
        if all(['amount_base' not in data, 'amount_quote' not in data]):
            raise ValidationError(
                _('One of amount_quote and amount_base is required.'))

        _addr_keys = self._get_address_keys(data)

        base_code = pair_obj.base.code
        validate_base_address = get_validator(base_code)
        validate_base_address(data[_addr_keys['base_address']]['address'])
        quote_code = pair_obj.quote.code
        validate_quote_address = get_validator(quote_code)
        validate_quote_address(data[_addr_keys['quote_address']]['address'])
        return super(CreateLimitOrderSerializer, self).validate(data)

    def create(self, validated_data):
        for field in READABLE_FIELDS:
            validated_data.pop(field, None)
        withdraw_address = validated_data.pop('withdraw_address')
        refund_address = validated_data.pop('refund_address')
        validated_data.pop('pair')
        withdraw_addr_list = Address.objects.filter(
            address=withdraw_address['address']
        )
        order = LimitOrder(pair=self.pair, order_book=self.order_book,
                           **validated_data)
        if not withdraw_addr_list:
            w_address = Address(**withdraw_address)
            w_address.type = Address.WITHDRAW
            w_address.currency = order.withdraw_currency
            w_address.save()
        else:
            w_address = withdraw_addr_list[0]

        order.withdraw_address = w_address
        refund_addr_list = Address.objects.filter(
            address=refund_address['address']
        )
        if not refund_addr_list:
            r_address = Address(**refund_address)
            r_address.type = Address.REFUND
            r_address.currency = order.refund_currency
            r_address.save()
        else:
            r_address = refund_addr_list[0]
        order.refund_address = r_address
        try:
            order.save()
            # get post_save stuff in sync
            order.refresh_from_db()
            return order
        except ValidationError as e:
            raise RestValidationError({'non_field_errors': [e.message]})

    def update(self, instance, validated_data):
        # Forbid updating after creation
        return instance
