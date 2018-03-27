from rest_framework import serializers


class PrivateField(serializers.ReadOnlyField):

    def get_attribute(self, instance):
        """
        Given the *outgoing* object instance, return the primitive value
        that should be used for this field.
        """
        if getattr(instance, 'user') == self.context['request'].user:
            return super(PrivateField, self).get_attribute(instance)
        return None
