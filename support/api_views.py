from core.common.api_views import UserResourceViewSet
from .serializers import SupportSerializer
from .models import Support
from .task_summary import send_support_email


class SupportViewSet(UserResourceViewSet):
    lookup_field = 'unique_reference'
    serializer_class = SupportSerializer
    http_method_names = ['post']

    def get_queryset(self):
        if self.request.user.is_authenticated:
            self.queryset = Support.objects.filter(user=self.request.user)
        else:
            self.queryset = []

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            response_object = serializer.save(user=self.request.user)
        else:
            response_object = serializer.save()
        send_support_email.apply_async([response_object.pk])
        return response_object
