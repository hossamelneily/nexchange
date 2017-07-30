from rest_framework import viewsets
from nexchange.permissions import NoUpdatePermission, OwnerOnlyPermission


class FlattenMixin:
    """Flattens the specified related objects in this representation"""
    def to_representation(self, obj):
        assert hasattr(self.Meta, 'flatten'), (
            'Class {serializer_class} missing "Meta.flatten" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        # Get the current object representation
        rep = super(FlattenMixin, self).to_representation(obj)
        # Iterate the specified related objects with their serializer
        for field, serializer_class in self.Meta.flatten:
            serializer = serializer_class(context=self.context)
            objrep = serializer.to_representation(getattr(obj, field))
            # Include their fields, prefixed, in the current representation
            for key in objrep:
                rep[field + "_" + key] = objrep[key]
        return rep


class UserResourceViewSet(viewsets.ModelViewSet):
    permission_classes = (NoUpdatePermission, OwnerOnlyPermission,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        super(UserResourceViewSet, self).perform_create(serializer)
