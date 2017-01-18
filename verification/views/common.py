from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View


class LoginRestrictedView(View):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRestrictedView, self).dispatch(
            request, *args, **kwargs
        )
