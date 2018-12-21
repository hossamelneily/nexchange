from django.core.management import BaseCommand
from orders.models import Order
from decimal import Decimal
from payments.utils import money_format


class Command(BaseCommand):
    help = "Audit Auto Trade"
    ETH_WALLETS = [
        '0xf0A3F9D050bcdb1A00b1d21f52c465A9D5F384c8',
        '0xd8f09b44b7bAB63f712FeecD9Dfd7a6443287dcD',
        '0x83B91ACFD7D528568bf2eC7BC05Cc579a4a4e5D7'
    ]
    BTC_WALLETS = ['15TpiR1wMZKQAGz2Z5djUae2PPkRLpDv4H']
    LTC_WALLETS = ['LZwCreaten4kjKoBd5ZgYv65roL7JWxzzT']
    DOGE_WALLETS = ['DG3p9uL6C2pf6qLVWSJVhDCNXh6qndjAdF']
    ALL_WALLETS = ETH_WALLETS + BTC_WALLETS + LTC_WALLETS + DOGE_WALLETS

    def print_orders(self, orders):
        print(
            '#', 'date', 'time', 'order_ref', 'pair', 'amount_quote', 'quote_code',
            'amount_base', 'base_code', 'markup_fee_quote', 'with_fee_quote',
            'deposit_fee_quote', 'markup_fee_base', 'with_fee_base',
            'deposit_fee_base',
            'with_markup_from_db', 'deposit_tx_id', 'withdraw_tx_id'
        )
        tot_with_quote = tot_dep_quote = tot_markup_quote = Decimal('0')
        tot_with_base = tot_dep_base = tot_markup_base = Decimal('0')
        tot_amount_base = tot_amount_quote = Decimal('0')
        for i, order in enumerate(orders):
            with_tx_id = order.transactions.get(type='W').tx_id
            dep_tx_id = order.transactions.get(type='D').tx_id
            fees = order.orderfee_set.all()
            with_markup_fees_from_db = False
            if fees:
                with_fee = fees.get(fee_source__name='Withdrawal')
                markup_fee = fees.get(fee_source__name='Markup')
                with_fee_quote = with_fee.amount_quote
                with_fee_base = with_fee.amount_base
                markup_fee_quote = markup_fee.amount_quote
                markup_fee_base = markup_fee.amount_base
                with_markup_fees_from_db = True
            else:
                with_fee_base = order.withdrawal_fee
                with_fee_quote = order.withdrawal_fee_quote
                markup_multiplier = \
                    Decimal('1') / (Decimal('1') + order.pair.fee_ask) \
                    * order.pair.fee_ask
                markup_fee_quote = money_format(
                    (order.amount_quote - with_fee_quote) * markup_multiplier,
                    places=8
                )
                markup_fee_base = money_format(
                    (order.amount_base - with_fee_base) * markup_multiplier,
                    places=8
                )
                with_fee_base = money_format(with_fee_base, places=8)
                with_fee_quote = money_format(with_fee_quote, places=8)
            if order.pair.quote.code == 'ETH':
                # Ethereum wallet transfer fee
                deposit_fee_quote = Decimal('0.00105')
            elif order.pair.quote.code == 'BTC':
                # bittrex withdrawal fee
                deposit_fee_quote = Decimal('0.0005')
            elif order.pair.quote.code == 'DOGE':
                # bittrex withdrawal fee
                deposit_fee_quote = Decimal('2')
            elif order.pair.quote.code == 'LTC':
                # bittrex withdrawal fee
                deposit_fee_quote = Decimal('0.01')
            deposit_fee_base = money_format(
                deposit_fee_quote * with_fee_base / with_fee_quote,
                places=8
            )
            print(
                i + 1, order.created_on, order.unique_reference, order.pair.name,
                order.amount_quote, order.pair.quote.code, order.amount_base,
                order.pair.base.code, markup_fee_quote, with_fee_quote,
                deposit_fee_quote, markup_fee_base, with_fee_base,
                deposit_fee_base, with_markup_fees_from_db, with_tx_id,
                dep_tx_id
            )
            tot_dep_quote += deposit_fee_quote
            tot_dep_base += deposit_fee_base
            tot_markup_quote += markup_fee_quote
            tot_markup_base += markup_fee_base
            tot_with_quote += with_fee_quote
            tot_with_base += with_fee_base
            tot_amount_base += order.amount_base
            tot_amount_quote += order.amount_quote
        tot_fees_quote = tot_dep_quote + tot_markup_quote + tot_with_quote
        tot_fees_base = tot_dep_base + tot_markup_base + tot_with_base
        print()
        print(
            'Total {count} {pair} orders.Volume {tot_amount_base}{base}'
            '({tot_amount_quote}{quote}). Total fees '
            '{tot_fees_quote}{quote}({tot_fees_base}{base}): withdrawal fees '
            '{with_fees_quote}{quote}({with_fees_base}{base}), deposit fees '
            '{dep_fees_quote}{quote}({dep_fees_base}{base}), markup fees '
            '{markup_fees_quote}{quote}({markup_fees_base}{base})'.format(
                count=orders.count(),
                pair=order.pair.name,
                tot_fees_quote=tot_fees_quote,
                tot_fees_base=tot_fees_base,
                quote=order.pair.quote.code,
                with_fees_quote=tot_with_quote,
                with_fees_base=tot_with_base,
                dep_fees_quote=tot_dep_quote,
                dep_fees_base=tot_dep_base,
                markup_fees_quote=tot_markup_quote,
                markup_fees_base=tot_markup_base,
                base=order.pair.base.code,
                tot_amount_base=tot_amount_base,
                tot_amount_quote=tot_amount_quote
            )
        )
        print()
        base = order.pair.base.code
        quote = order.pair.quote.code
        print('fee_name', 'quote({})'.format(quote), 'base({})'.format(base))
        print('Markup', tot_markup_quote, tot_markup_base)
        print('Withdrawal', tot_with_quote, tot_with_base)
        print('Deposit', tot_dep_quote, tot_dep_base)
        print('Total', tot_fees_quote, tot_fees_base)
        print()
        print('Volume_quote({})'.format(quote), 'Volume_base({})'.format(base))
        print(tot_amount_quote, tot_amount_base)
        print()
        print()
        return {
            order.pair.name: {
                'positions': {
                    base: tot_amount_base, quote: -tot_amount_quote
                },
                'fees': {base: tot_fees_base, quote: tot_fees_quote},
                'deposit_fees': {quote: tot_dep_quote}
            }}

    def handle(self, *args, **options):
        res = {}
        first_order = Order.objects.get(unique_reference='OSGUZG')
        all_orders = Order.objects.filter(
            withdraw_address__address__in=self.ALL_WALLETS,
            status=Order.COMPLETED, created_on__gte=first_order.created_on
        ).order_by('created_on')
        btceth_orders = all_orders.filter(pair__name__in=['BTCETH'])
        res.update(self.print_orders(btceth_orders))
        ethbtc_orders = all_orders.filter(pair__name__in=['ETHBTC'])
        res.update(self.print_orders(ethbtc_orders))
        dogeeth_orders = all_orders.filter(pair__name__in=['DOGEETH'])
        res.update(self.print_orders(dogeeth_orders))
        ethdoge_orders = all_orders.filter(pair__name__in=['ETHDOGE'])
        res.update(self.print_orders(ethdoge_orders))
        ltceth_orders = all_orders.filter(pair__name__in=['LTCETH'])
        res.update(self.print_orders(ltceth_orders))
        ethltc_orders = all_orders.filter(pair__name__in=['ETHLTC'])
        res.update(self.print_orders(ethltc_orders))

        positions = {}
        deposit_fees = {}
        for key, value in res.items():
            for k, v in value['positions'].items():
                if k in positions:
                    positions[k] += v
                else:
                    positions[k] = v
            for k, v in value['deposit_fees'].items():
                if k in deposit_fees:
                    deposit_fees[k] += v
                else:
                    deposit_fees[k] = v

        print('CURRENCY', 'POSITION')
        for k, v in positions.items():
            print(k, v)

        print('CURRENCY', 'DEPOSIT_FEES')
        for k, v in deposit_fees.items():
            print(k, v)

        print('CURRENCY', 'POSITION-DEPOSIT_FEES')
        for k, v in positions.items():
            print(k, v - deposit_fees[k])
        print('Audit')

