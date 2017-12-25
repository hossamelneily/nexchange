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
    try:
        bcbytes = decode_base58(value, 25)
    except ValueError:
        raise ValidationError(
            _('%(value)s is not a valid address'),
            params={'value': value},
        )
    if not bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]:
        raise ValidationError(
            _('%(value)s is not a valid address'),
            params={'value': value},
        )


def validate_btc(value):
    p = re.compile(
        "^(1|3)[1-9A-Za-z]{25,34}$"
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


def validate_rns(value):
    p = re.compile(
        "^R[1-9A-Za-z]{25,34}$"
    )

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Renos address'),
            params={'value': value},
        )
    validate_bc(value)


def validate_doge(value):
    p = re.compile(
        "^D[1-9A-Za-z]{25,34}$"
    )

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Doge address'),
            params={'value': value},
        )
    validate_bc(value)


def validate_xvg(value):
    p = re.compile(
        "^D[1-9A-Za-z]{25,34}$"
    )

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Verge address'),
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


def validate_xrb(value):
    p = re.compile('^xrb_(1|3)[0-9a-zA-Z]{59}$')
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
    elif value[:1] in ['1', '3']:
        validate_btc(value)
    elif value[:1] == 'L':
        validate_ltc(value)
    elif value[:1] == 'D':
        validate_doge(value)
    else:
        validate_bc(value)


def validate_non_address(value):
    raise ValidationError(
        _('%(value)s is an invalid address'),
        params={'value': value},
    )


def get_validator(code):
    if code in ['ETH', 'BDG', 'OMG', 'GNT', 'QTM', 'EOS']:
        return validate_eth
    elif code in ['BTC', 'BCH']:
        return validate_btc
    elif code == 'LTC':
        return validate_ltc
    elif code == 'RNS':
        return validate_rns
    elif code == 'DOGE':
        return validate_doge
    elif code == 'XVG':
        return validate_xvg
    elif code == 'XRB':
        return validate_xrb

    return validate_non_address
