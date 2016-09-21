from decimal import Decimal


def money_format(value, is_numeric=True, places=2, curr='', sep=',', dp='.',
                 pos='', neg='-', trailneg=''):
    q = Decimal(10) ** -places  # 2 places --> '0.01'
    if is_numeric:
        return value.quantize(q)
    sign, digits, exp = value.quantize(q).as_tuple()
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
