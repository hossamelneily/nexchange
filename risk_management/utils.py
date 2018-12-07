from core.models import Currency, Pair


def get_native_pairs():
    crypto = Currency.objects.filter(is_crypto=True).exclude(
        code__in=['RNS']).order_by('pk')
    codes = [curr.code for curr in crypto] + ['EUR', 'USD', 'GBP',
                                              'JPY']
    names = []
    for i, code_base in enumerate(codes):
        for code_quote in codes[i + 1:]:
            names.append('{}{}'.format(code_base, code_quote))
    # old ticker search requires a lot of time therefore disable_
    # ticker=True pairs (pairs with relatively old last tickers) are
    # excluded
    return Pair.objects.filter(name__in=names).exclude(
        disable_ticker=True
    )
