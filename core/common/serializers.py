from rest_framework import serializers


class PartialModelSerializer(serializers.ModelSerializer):
    """Like ModelSerializers - but accepts partial updates with PUT"""

    def __init__(self, *args, **kwargs):
        super(PartialModelSerializer, self).__init__(*args, **kwargs)

        request = self.context.get('request')

        if request and request.method == 'PUT':
            self.partial = True
