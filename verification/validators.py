from django.conf import settings
import os
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def validate_image_extension(value):
    allowed_exts = settings.ALLOWED_IMAGE_FILE_EXTENSIONS
    ext = os.path.splitext(value.name)[1]
    valid_extensions = allowed_exts
    allowed_str_list = ', '.join(x[1:].upper() for x in allowed_exts)
    error_msg = _(
        'Unsupported file extension. Please use one of these file formats: '
        '{}.'.format(allowed_str_list))
    if not ext.lower() in valid_extensions:
        raise ValidationError(error_msg)
