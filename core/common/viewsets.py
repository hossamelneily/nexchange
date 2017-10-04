from rest_framework import mixins, viewsets


class NoDeleteModelViewSet(mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`,
    `partial_update()`, and `list()` actions.
    Like ModelViewSet but without DELETE ("destroy()").
    Also includes the UpdateUserMixin.
    """