import mimetypes
import os
from wsgiref.util import FileWrapper

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseRedirect, HttpResponseBadRequest)
from django.shortcuts import render
from django.utils.encoding import smart_str
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView

from verification.forms import VerificationUploadForm
from verification.models import Verification, VerificationDocument,\
    KycPushRequest, DocumentType

from verification.views.common import LoginRestrictedView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from nexchange.utils import get_client_ip
import json
from orders.models import Order
from payments.models import Payment
from urllib.parse import urlparse
import requests


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


class IdenfyListenView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(IdenfyListenView, self).dispatch(request,
                                                      *args, **kwargs)

    def get_or_create_kyc(self, note):
        _kycs = Verification.objects.filter(note=note)
        kyc = _kycs.latest('id') if _kycs else Verification.objects.create(
            note=note
        )
        orders = Order.objects.filter(unique_reference=note)
        order = orders.latest('id') if orders else None
        if orders and not kyc.payment_preference:
            payments = order.payment_set.filter(type=Payment.DEPOSIT)
            if payments:
                payment = payments.latest('id')
                pref = payment.payment_preference
                kyc.payment_preference = pref
                kyc.save()
        return kyc, order

    def validate_push(self, kyc_push):
        kyc_push.valid_link = False
        files_urls = kyc_push.get_payload_dict().get('fileUrls', {})
        try:
            kyc_push.valid_link = True
            check_url = [v for v in files_urls.values()][0]
            _parsed = urlparse(check_url)
            if 'ivs.idenfy.com' == _parsed.netloc and _parsed.scheme == 'https':  # noqa
                resp = requests.get(check_url)
                kyc_push.valid_link = resp.status_code == 200
        except IndexError:
            pass
        kyc_push.save()
        return kyc_push

    def post(self, request):
        try:
            ip = get_client_ip(request)
            kyc_push = KycPushRequest(ip=ip)
            kyc_push.save()
            payload = json.loads(request.body)
            kyc_push.set_payload(payload)
            kyc_push.save(reload_from_payload=True)
            note = payload.get('clientId')
            kyc, order = self.get_or_create_kyc(note)
            kyc_push = self.validate_push(kyc_push)
            if kyc_push.document_status == kyc.OK:
                kyc.full_name = kyc_push.full_name
                kyc.save(update_fields=['full_name'])
                if order:
                    token = order.identitytoken_set.latest('id')
                    token.used = True
                    token.save()

            VerificationDocument.objects.create(
                kyc_push=kyc_push,
                document_type=DocumentType.objects.get(name='ID'),
                verification=kyc,
                contains_selfie=True
            )
            return HttpResponse()
        except Exception:
            return HttpResponseBadRequest()
