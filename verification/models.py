from django.contrib.auth.models import User
from django.db import models

from core.common.models import SoftDeletableModel, TimeStampedModel


class Verification(TimeStampedModel, SoftDeletableModel):

    TYPES = (
        ('REJECTED', 'Rejected'),
        ('OK', 'Approved'),
    )

    def _get_file_name(self, filename, root):
        return '/'.join([str(self.user.username), root, filename])

    def identity_file_name(self, filename, root='verification/identity_docs'):
        return self._get_file_name(filename, root)

    def _utility_file_name(self, filename, root='verification/utility_docs'):
        return self._get_file_name(filename, root)

    user = models.ForeignKey(User)
    identity_document = models.ImageField(
        upload_to=identity_file_name
    )
    utility_document = models.ImageField(
        upload_to=_utility_file_name
    )
    id_status = models.CharField(choices=TYPES, max_length=10, null=True,
                                 blank=True)
    util_status = models.CharField(choices=TYPES, max_length=10, null=True,
                                   blank=True)
