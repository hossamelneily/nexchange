from rest_framework import serializers
from payments.utils import money_format
from decimal import Decimal


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


class BaseOrderSerializer(serializers.ModelSerializer):

    def strip_payload_decimal(self, data, key):
        _raw = data.get(key, None)
        if _raw:
            try:
                _value = Decimal(str(_raw))
                _formatted = money_format(_value, places=8)
                data[key] = _formatted
            except Exception:
                pass
        return data
