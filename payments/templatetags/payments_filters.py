from django.template import Library

register = Library()


@register.filter
def any_values(values_dict, is_buy):
    attr = 'buy_enabled' if is_buy else 'sell_enabled'
    return any([val and getattr(val, attr) for val in values_dict.values()])


@register.filter
def is_in(val, val_list):
    val_list = val_list.split(',')
    return val in val_list
