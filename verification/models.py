from django.contrib.auth.models import User
from django.db import models

from core.common.models import SoftDeletableModel, TimeStampedModel


class Verification(TimeStampedModel, SoftDeletableModel):

    TYPES = (
        ('REJECTED', 'Rejected'),
        ('NONE', 'Waiting For Approval'),
        ('OK', 'Approved'),
    )

    user = models.ForeignKey(User)
    identity_document = models.ImageField(
        upload_to='verification/identity_documents', null=True
    )
    utility_document = models.ImageField(
        upload_to='verification/utility_document', null=True
    )
    id_status = models.CharField(choices=TYPES, default='NONE', max_length=10)
    util_status = models.CharField(choices=TYPES, default='NONE', max_length=10)
