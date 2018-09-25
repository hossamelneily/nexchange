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
        "^(L|M)[1-9A-Za-z]{25,34}$"
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


def validate_nano(value):
    p = re.compile('^xrb_(1|3)[0-9a-zA-Z]{59}$')
    p.match(value)

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Nano address'),
            params={'value': value},
        )
    # TODO: add ETH hash validation


def validate_usdt(value):
    p = re.compile('^1[1-9A-Za-z]{33}$')
    p.match(value)

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Tether address'),
            params={'value': value},
        )
    validate_bc(value)


def validate_zec(value):
    p = re.compile('^t[1-9A-Za-z]{34}$')
    p.match(value)

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Tether address'),
            params={'value': value},
        )


def validate_xmr(value):
    p = re.compile('^[4|8][0-9a-zA-Z]{94}$')
    p.match(value)

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Monero address'),
            params={'value': value},
        )


def validate_bch(value):
    p = re.compile('^bitcoincash:q[0-9a-z]{41}$')
    p.match(value)

    if not p.match(value):
        p = re.compile('^(1|3)[1-9A-Za-z]{25,34}$')
        validate_bc(value)
        if not p.match(value):
            raise ValidationError(
                _('%(value)s has invalid characters for a valid Bitcoin '
                  'Cash address'),
                params={'value': value},
            )


def validate_dash(value):
    p = re.compile('^X[0-9a-zA-Z]{33}$')
    p.match(value)

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Dash address'),
            params={'value': value},
        )


def validate_xrp(value):
    p = re.compile(
        "^r[1-9A-Za-z][^lO0I]{25,34}$"
    )

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters for a valid Ripple address'),
            params={'value': value},
        )


def validate_address(value):
    if value[:2] == '0x':
        validate_eth(value)
    elif value[:1] in ['1', '3']:
        validate_btc(value)
    elif value[:1] == 'L':
        validate_ltc(value)
    elif value[:1] == 'D':
        validate_doge(value)
    elif value[:1] == 't':
        validate_zec(value)
    elif value[:1] in ['4', '8']:
        validate_xmr(value)
    elif value[:13] == 'bitcoincash:q':
        validate_bch(value)
    elif value[:1] == 'X':
        validate_dash(value)
    elif value[:1] == 'r':
        validate_xrp(value)
    else:
        validate_bc(value)


def validate_non_address(value):
    raise ValidationError(
        _('%(value)s is an invalid address'),
        params={'value': value},
    )


def validate_xmr_payment_id(value):
    p = re.compile('^(?=[0-9A-Za-z]*$)(?:.{16}|.{64})$')
    p.match(value)

    if not p.match(value):
        raise ValidationError(
            _('%(value)s has invalid characters '
              'for a valid Monero payment id'),
            params={'value': value},
        )


def validate_destination_tag(value):
    def raise_error():
        raise ValidationError(
            _('%(value)s is not valid destination tag'),
            params={'value': value},
        )
    p = re.compile("^[0-9]+$")
    is_correct = True if p.match(value) else False
    if not is_correct:
        raise_error()

    int_value = int(value)
    if value != str(int_value) or not 0 <= int(value) < 2**32:
        raise_error()


def get_validator(code):
    if code in ['ETH', 'BDG', 'OMG', 'GNT', 'QTM',
                'EOS', 'KCS', 'BNB', 'KNC', 'BIX',
                'HT', 'BNT', 'COSS', 'COB', 'BMH']:
        return validate_eth
    elif code in ['BTC']:
        return validate_btc
    elif code == 'LTC':
        return validate_ltc
    elif code == 'RNS':
        return validate_rns
    elif code == 'DOGE':
        return validate_doge
    elif code == 'XVG':
        return validate_xvg
    elif code == 'NANO':
        return validate_nano
    elif code == 'ZEC':
        return validate_zec
    elif code == 'USDT':
        return validate_usdt
    elif code == 'XMR':
        return validate_xmr
    elif code == 'BCH':
        return validate_bch
    elif code == 'DASH':
        return validate_dash
    elif code == 'XRP':
        return validate_xrp

    return validate_non_address
