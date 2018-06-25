from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template

from core.common.api_views import DateFilterViewSet
from referrals.models import ReferralCode
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from .models import Referral
from .serializers import ReferralSerializer
from rest_framework.permissions import IsAuthenticated


class ReferralViewSet(DateFilterViewSet):
    serializer_class = ReferralSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get']

    def get_queryset(self, *args, **kwargs):
        self.queryset = \
            Referral.objects.filter(code__user=self.request.user)
        return super(ReferralViewSet, self).get_queryset()


@login_required
def referrals(request):
    template = get_template('referrals/index_referrals.html')
    user = request.user
    referral_codes = ReferralCode.objects.filter(user=user)
    referrals_list = Referral.objects.filter(code__in=referral_codes,
                                             referee__isnull=False)
    # return JsonResponse({'tests': referrals_[0].turnover})

    paginate_by = 10
    paginator = Paginator(referrals_list, paginate_by)
    page = request.GET.get('page')

    try:
        referrals_list = paginator.page(page)

    except PageNotAnInteger:
        referrals_list = paginator.page(1)

    except EmptyPage:
        referrals_list = paginator.page(paginator.num_pages)

    return HttpResponse(template.render({'referrals_list': referrals_list},
                                        request))


@method_decorator(login_required, name='dispatch')
class ReferralCodeCreateView(View):

    def post(self, request):
        success_msg = _('New Referral Code Created')

        code = request.POST.get('code_new')
        comment = request.POST.get('comment')
        old_refs = ReferralCode.objects.filter(code=code)
        if len(old_refs) > 0:
            msg = _('Referral Code {} already exists.'.format(code))
            return JsonResponse({'status': 'ERROR', 'msg': msg}, safe=False)
        new_code = ReferralCode(user=request.user, code=code, comment=comment)
        new_code.save()

        redirect_url = reverse('accounts.user_profile') + '?tab=referrals'
        return JsonResponse({
            'status': 'OK', 'redirect': redirect_url, 'msg': success_msg},
            safe=False
        )
