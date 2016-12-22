from django.views.generic.edit import FormView
from django.views.generic import TemplateView

from support.forms import SupportForm


class SupportView(FormView):
    template_name = 'support/support.html'
    form_class = SupportForm
    success_url = '/support/thanks/'

    def get_form_kwargs(self):
        kwargs = super(SupportView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        object = form.save(commit=False)
        try:
            object.user = self.request.user
        except ValueError:
            object.user = None
        object.save()
        return super(SupportView, self).form_valid(form)


class ThanksView(TemplateView):
    template_name = 'support/thanks.html'
