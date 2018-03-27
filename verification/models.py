from django.contrib.auth.models import User
from django.db import models
from verification.validators import validate_image_extension

from core.common.models import SoftDeletableModel, TimeStampedModel
from payments.models import PaymentPreference
from django.core.urlresolvers import reverse


class Verification(TimeStampedModel, SoftDeletableModel):

    REJECTED = 'REJECTED'
    PENDING = 'PENDING'
    OK = 'OK'
    TYPES = (
        (REJECTED, 'Rejected'),
        (PENDING, 'Pending'),
        (OK, 'Approved'),
    )

    def _get_file_name(self, filename, root):
        if self.payment_preference and \
                self.payment_preference.provider_system_id:
            root1 = self.payment_preference.provider_system_id
        elif self.user:
            root1 = self.user.username
        else:
            root1 = 'all'
        return '/'.join([root1, root, filename])

    def identity_file_name(self, filename, root='verification/identity_docs'):
        return self._get_file_name(filename, root)

    def _utility_file_name(self, filename, root='verification/utility_docs'):
        return self._get_file_name(filename, root)

    user = models.ForeignKey(User, null=True, blank=True)
    payment_preference = models.ForeignKey(PaymentPreference, null=True,
                                           blank=True)
    identity_document = models.FileField(
        upload_to=identity_file_name, validators=[validate_image_extension],
        blank=True, null=True
    )
    utility_document = models.FileField(
        upload_to=_utility_file_name, validators=[validate_image_extension],
        blank=True, null=True
    )
    id_status = models.CharField(choices=TYPES, max_length=10, null=True,
                                 blank=True, default=PENDING)
    util_status = models.CharField(choices=TYPES, max_length=10, null=True,
                                   blank=True, default=PENDING)
    full_name = models.CharField(max_length=30, null=True, blank=True)
    note = models.CharField(max_length=30, null=True, blank=True)
    user_visible_comment = models.CharField(max_length=255,
                                            null=True, blank=True)

    def id_doc(self):
        if self.identity_document:
            link = '<a href="{}">"Download ID"</a>'.format(
                reverse('verification.download',
                        kwargs={'file_name': self.identity_document.name}),
            )
        else:
            link = '-'
        return link

    def residence_doc(self):
        if self.utility_document:
            link = '<a href="{}">"Download UTIL"</a>'.format(
                reverse('verification.download',
                        kwargs={'file_name': self.utility_document.name}),
            )
        else:
            link = '-'
        return link

    id_doc.allow_tags = True
    residence_doc.allow_tags = True
