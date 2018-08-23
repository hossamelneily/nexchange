import mimetypes
import os
from wsgiref.util import FileWrapper

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseRedirect)
from django.shortcuts import render
from django.utils.encoding import smart_str
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView

from verification.forms import VerificationUploadForm
from verification.models import Verification, VerificationDocument

from verification.views.common import LoginRestrictedView


class Upload(LoginRestrictedView, CreateView):
    template_name = 'verification/upload.html'
    model = Verification
    form_class = VerificationUploadForm
    success_url = reverse_lazy('verification.upload')

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.user = self.request.user
        instance.save()
        return HttpResponseRedirect(self.success_url)

    def get(self, request, form=None):
        filters = {}
        filters['user'] = self.request.user
        verification_list = self.model.objects.filter(**filters)
        if form is None:
            form = self.form_class(initial=self.initial)

        return render(request, self.template_name,
                      {'verifications': verification_list,
                       'verification_form': form})

    def post(self, request):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.get(request, form=form)


@login_required
def download(request, file_name):

    verifications = Verification.objects.filter(
        Q(identity_document=file_name) | Q(utility_document=file_name)
    )
    verification_docs = VerificationDocument.objects.filter(
        document_file=file_name
    )
    if verifications:
        verification = verifications.latest('id')
    elif verification_docs:
        doc = verification_docs.latest('id')
        verification = doc.verification
    else:
        return HttpResponseForbidden(
            _('Verification not found')
        )

    if all([not verification.user == request.user,
            not request.user.is_staff]):
        return HttpResponseForbidden(
            _('You don\'t have permission to download this document')
        )

    file_path = settings.MEDIA_ROOT + '/' + file_name
    file_wrapper = FileWrapper(open(file_path, 'rb'))
    file_mimetype = mimetypes.guess_type(file_path)
    response = HttpResponse(file_wrapper, content_type=file_mimetype)
    response['X-Sendfile'] = file_path
    response['Content-Length'] = os.stat(file_path).st_size
    response['Content-Disposition'] = 'attachment; filename={}'.format(
        smart_str(file_name)
    )
    return response
