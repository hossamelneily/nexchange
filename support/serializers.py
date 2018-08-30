from rest_framework import serializers
from .models import Support


class SupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Support
        fields = ('unique_reference', 'created_on', 'modified_on',
                  'name', 'email', 'telephone',
                  'subject', 'message', 'is_resolved')

        read_only_fields = ('unique_reference', 'is_resolved',
                            'created_on', 'modified_on',)
