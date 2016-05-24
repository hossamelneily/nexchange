from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from hashlib import sha256


def decode_base58(bc, length):
    digits58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n = 0
    for char in bc:
        n = n * 58 + digits58.index(char)
    return n.to_bytes(length, 'big')


def validate_bc(bc):
    bcbytes = decode_base58(bc, 25)
    if not bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]:
        raise ValidationError(
            _('%(value)s is not a valid bit coin address'),
            params={'value': value},
        )
