import re
from hashlib import sha256

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def decode_base58(bc, length):
    digits58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n = 0
    for char in bc:
        n = n * 58 + digits58.index(char)
    return n.to_bytes(length, 'big')


def validate_bc(value):
    '''Validate that the address informed is a valid bit coin address
    Adapted from https://rosettacode.org/wiki/Bitcoin/address_validation#Python
    Using length 26-35, according to http://bitcoin.stackexchange.com/a/36948
    '''
    bcbytes = decode_base58(value, 25)
    if not bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]:
        raise ValidationError(
            _('%(value)s is not a valid address'),
            params={'value': value},
        )


def validate_btc(value):
    p = re.compile(
        "^1[1-9A-Za-z]{25,34}$"
    )

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Bitcoin address'),
            params={'value': value},
        )
    validate_bc(value)


def validate_ltc(value):
    p = re.compile(
        "^L[1-9A-Za-z]{25,34}$"
    )

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Litecoin address'),
            params={'value': value},
        )
    validate_bc(value)


def validate_eth(value):
    p = re.compile('^0x[0-9a-fA-F]{40}$')
    p.match(value)

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Ethereum address'),
            params={'value': value},
        )
    # TODO: add ETH hash validation


def validate_address(value):
    if value[:2] == '0x':
        validate_eth(value)
    elif value[:1] == '1':
        validate_btc(value)
    elif value[:1] == 'L':
        validate_ltc(value)
    else:
        raise ValidationError(
            _('%(value)s is invalid.'),
            params={'value': value},
        )
