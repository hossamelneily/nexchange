from core.common.views import DateFilterViewSet
from .serializers import ReferralSerializer
from .models import Referral
from .permissions import IsLoggedIn


class ReferralViewSet(DateFilterViewSet):
    serializer_class = ReferralSerializer
    premission_classes = (IsLoggedIn,)

    def get_queryset(self, *args, **kwargs):
        self.queryset = \
            Referral.objects.filter(code__user=self.request.user)
        return super(ReferralViewSet, self).get_queryset()
