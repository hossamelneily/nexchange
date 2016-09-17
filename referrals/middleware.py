from django.conf import settings
from referrals.models import ReferralCode, Referral


class ReferralMiddleWare(object):
    def process_request(self, request):
        if settings.REFERRER_GET_PARAMETER in request.GET:
            code = None
            str_code = \
                request.GET.get(settings.REFERRER_GET_PARAMETER, '').strip()
            str_code = str_code if str_code \
                else request.session[settings.REFERRAL_SESSION_KEY]
            if not str_code:
                return
            try:
                code = ReferralCode.objects.get(code=str_code)
            except ReferralCode.DoesNotExist:
                    pass

            finally:
                if code is not None and \
                        hasattr(request, 'user') and \
                        code.user != request.user:
                    request.session[settings.REFERRAL_SESSION_KEY] = code.code
                    ip = request.META['REMOTE_ADDR']
                    ref, created = \
                        Referral.objects.get_or_create(ip=str(ip), code=code)

                    # allow referral only if the user has no orders

                    if request.user.is_authenticated() \
                            and (not ref.referee or not
                                 ref.referee.orders_set.count()):
                        ref.referee = request.user
                        ref.save()
