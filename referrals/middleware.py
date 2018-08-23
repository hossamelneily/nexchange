from django.conf import settings

from referrals.models import Referral, ReferralCode
from nexchange.utils import get_client_ip, get_nexchange_logger
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction, IntegrityError
from django.utils.functional import SimpleLazyObject
from django.utils.deprecation import MiddlewareMixin


class ReferralMiddleWare(MiddlewareMixin):
    logger = get_nexchange_logger(__name__, True, True)

    def get_referral_code(self, request):
        # get from HEADER
        str_code = \
            request.META.get(settings.REFERRER_HEADER_INDEX, '').strip()

        # get from GET parameter
        if not str_code:
            str_code = \
                request.GET.get(settings.REFERRER_GET_PARAMETER, '').strip()

        str_code = str_code if str_code \
            else request.session.get(settings.REFERRAL_SESSION_KEY)

        code = None
        if str_code:
            try:
                code = ReferralCode.objects.get(code=str_code)
            except ReferralCode.DoesNotExist:
                self.logger.info('code {} not found'.format(str_code))
            except ReferralCode.MultipleObjectsReturned:
                self.logger.error(
                    'code {} multiple objects in db'.format(str_code)
                )
        return code

    def process_request(self, request):
        code = self.get_referral_code(request)
        if code is not None and \
                hasattr(request, 'user') and \
                code.user != request.user:
            request.session[settings.REFERRAL_SESSION_KEY] = code.code
            ip = get_client_ip(request)
            referee = request.user
            if isinstance(referee, SimpleLazyObject):
                # this is to avoid AnonymousUser which is used by
                # restframework. is_authenticated == False is not good here
                # because ordinary Anonymous***(order.user in most cases)
                # user is also not authenticated.
                return
            try:
                with transaction.atomic():
                    Referral.objects.get_or_create(ip=ip, code=code,
                                                   referee=referee)
            except MultipleObjectsReturned as e:
                self.logger.warning(
                    'Multiple refferrals.ip:{} code {}: :{}'.format(
                        ip, code.code, e))
            except IntegrityError as e:
                self.logger.warning(
                    'Unique referral constraint ip {} code . :{}'.format(
                        ip, code.code, e))
            finally:
                ref = Referral.objects.filter(ip=ip, code=code,
                                              referee=referee).last()
                # allow referral only if the user has no orders
                # todo use confirmed_orders_count (?)
                if all([ref, referee.is_authenticated,
                        not ref.confirmed_orders_count]):
                    # avoid executing this middleware on every request
                    request.session.pop(settings.REFERRAL_SESSION_KEY,
                                        None)
