from django import template

register = template.Library()


def ord_date(date):
    def convert_int(s):
        try:
            return int(s)
        except ValueError:
            return s

    def add_suffix(d):
        suffix = 'th' if 4 <= d % 100 <= 20\
            else {1: 'st', 2: 'nd', 3: 'rd'}\
            .get(d % 10, 'th')
        return '{}{}'.format(d, suffix)

    output = []
    fragments = date.split(' ')
    for frag in fragments:
        val = convert_int(frag)
        if isinstance(val, int) and 1 < val < 32:
            val = add_suffix(val)
        output.append(val)

    return ' '.join(output)


register.filter('ord_date', ord_date)
