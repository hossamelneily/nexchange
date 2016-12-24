from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from django.conf import settings

from support.forms import SupportForm


class SupportView(FormView):
    template_name = 'support/support.html'
    form_class = SupportForm
    success_url = '/support/thanks/'

    def get_form_kwargs(self):
        kwargs = super(SupportView, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(SupportView, self).get_context_data(**kwargs)
        cms_menu = []
        all_cms = [sf for sf in settings.CMSPAGES.values()]
        for a in all_cms:
            cms_menu = [sf for sf in a if 'support' in sf]
            if len(cms_menu) > 0:
                cms_menu = a
                break
        context['cmsmenu'] = cms_menu
        return context

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
