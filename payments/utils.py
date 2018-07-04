from decimal import Decimal, ROUND_HALF_UP
import base64
from hashlib import sha256


def money_format(value, is_numeric=True, places=2, curr='', sep=',', dp='.',
                 pos='', neg='-', trailneg=''):
    q = Decimal(10) ** -places  # 2 places --> '0.01'
    if is_numeric:
        return value.quantize(q, ROUND_HALF_UP)
    sign, digits, exp = value.quantize(q, ROUND_HALF_UP).as_tuple()
    result = []
    digits = list(map(str, digits))
    build, next = result.append, digits.pop
    if sign:
        build(trailneg)
    for i in range(places):
        build(next() if digits else '0')
    if places:
        build(dp)
    if not digits:
        build('0')
    i = 0
    while digits:
        build(next())
        i += 1
        if i == 3 and digits:
            i = 0
            build(sep)
    build(curr)
    build(neg if sign else pos)
    return ''.join(reversed(result))


def get_sha256_sign(ar_hash=(), upper=True, delimiter=':'):
    result_string = delimiter.join(ar_hash)
    sign_hash = sha256(result_string.encode('utf8'))
    sign = sign_hash.hexdigest()
    if upper:
        sign = sign.upper()
    return sign


def get_payeer_desc(description):
    desc = base64.b64encode(description.encode('utf8')).decode('utf8')
    return desc


def credit_card_number_validator(input):
    """ Luhn algorithm """
    digits = [int(c) for c in input if c.isdigit()]
    checksum = digits.pop()
    digits.reverse()
    doubled = [2 * d for d in digits[0::2]]
    total = sum(d - 9 if d > 9 else d for d in doubled) + sum(digits[1::2])
    return (total * 9) % 10 == checksum
