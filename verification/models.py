from django.contrib.auth.models import User
from django.db import models
from verification.validators import validate_image_extension

from core.common.models import SoftDeletableModel, TimeStampedModel


class Verification(TimeStampedModel, SoftDeletableModel):

    REJECTED = 'REJECTED'
    OK = 'OK'
    TYPES = (
        (REJECTED, 'Rejected'),
        (OK, 'Approved'),
    )

    def _get_file_name(self, filename, root):
        return '/'.join([str(self.user.username), root, filename])

    def identity_file_name(self, filename, root='verification/identity_docs'):
        return self._get_file_name(filename, root)

    def _utility_file_name(self, filename, root='verification/utility_docs'):
        return self._get_file_name(filename, root)

    user = models.ForeignKey(User)
    identity_document = models.FileField(
        upload_to=identity_file_name, validators=[validate_image_extension]
    )
    utility_document = models.FileField(
        upload_to=_utility_file_name, validators=[validate_image_extension]
    )
    id_status = models.CharField(choices=TYPES, max_length=10, null=True,
                                 blank=True)
    util_status = models.CharField(choices=TYPES, max_length=10, null=True,
                                   blank=True)
