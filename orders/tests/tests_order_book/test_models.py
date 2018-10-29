from core.tests.base import OrderBaseTestCase
from orders.models import LimitOrder, Trade, OrderBook
from core.models import Pair, Transaction, Address
from decimal import Decimal
from rest_framework.test import APIClient
from accounts.task_summary import import_transaction_deposit_scrypt_invoke,\
    update_pending_transactions_invoke
from core.tests.base import SCRYPT_ROOT
from unittest.mock import patch
from django.core.exceptions import ValidationError
from orders.task_summary import exchange_order_release_periodic


class LimitOrderSimpleTest(OrderBaseTestCase):

    def __init__(self, *args, **kwargs):
        self.api_client = APIClient()
        super(LimitOrderSimpleTest, self).__init__(*args, **kwargs)
        self.btc_address = '17dBqMpMr6r8ju7BoBdeZiSD3cjVZG62yJ'
        self.btc_refund_address = '19WohWYGczxYFxujHMVSRuCJijtc1b3bLg'
        self.doge_address = 'D97ankmH7a9tWaaDNUwnGgmDqcyNgQw5s1'
        self.doge_refund_address = 'DCsymFm1YRMBYA75BSrM4MQCxBCvRzRj9J'

    def setUp(self, *args, **kwargs):
        super(LimitOrderSimpleTest, self).setUp(*args, **kwargs)
        self.main_pair = Pair.objects.get(name="DOGEBTC")
        self.order_book = OrderBook.objects.create(pair=self.main_pair)

    def _create_limit_order_api(self, amount_base=None, amount_quote=None,
                                limit_rate=None, pair_name=None,
                                refund_address=None, withdraw_address=None,
                                order_type=None):
        if pair_name is None:
            pair_name = self.main_pair.name
        if order_type is None:
            order_type = LimitOrder.BUY
        if refund_address is None:
            refund_address = \
                self.btc_refund_address if order_type == LimitOrder.BUY \
                    else self.doge_refund_address  # noqa
        if withdraw_address is None:
            withdraw_address = \
                self.doge_address if order_type == LimitOrder.BUY \
                    else self.btc_address  # noqa
        order_data = {
            'order_type': order_type,
            "pair": {
                "name": pair_name
            },
            "withdraw_address": {
                "address": withdraw_address
            },
            "refund_address": {
                "address": refund_address
            }
        }
        if amount_base:
            order_data['amount_base'] = amount_base
        if amount_quote:
            order_data['amount_quote'] = amount_quote
        if limit_rate:
            order_data['limit_rate'] = limit_rate
        order_api_url = '/en/api/v1/limit_order/'
        response = self.api_client.post(
            order_api_url, order_data, format='json')
        order = LimitOrder.objects.get(
            unique_reference=response.json()['unique_reference']
        )
        return order

    def test_status_only_forward(self):
        limit_order = self._create_limit_order_api(
            limit_rate=1,
            amount_quote=1,
        )
        limit_order.status = LimitOrder.PAID_UNCONFIRMED
        limit_order.book_status = LimitOrder.OPEN
        limit_order.save()
        with self.assertRaises(ValidationError):
            limit_order.status = LimitOrder.INITIAL
            limit_order.save()
        with self.assertRaises(ValidationError):
            limit_order.book_status = LimitOrder.NEW
            limit_order.save()

    def test_calculate_order(self):
        amount_base = Decimal('1')
        limit_rate = Decimal('2')
        amount_quote = Decimal('2')
        order_base_quote = self._create_limit_order_api(
            amount_base=1,
            amount_quote=2,
        )
        order_base_quote.admin_comment = 'base_quote'
        order_base_quote.save()
        order_base_limit = self._create_limit_order_api(
            amount_base=1,
            limit_rate=2,
        )
        order_base_limit.admin_comment = 'base_limit'
        order_base_limit.save()
        order_quote_limit = self._create_limit_order_api(
            limit_rate=2,
            amount_quote=2,
        )
        order_quote_limit.admin_comment = 'quote_limit'
        for o in [order_base_limit, order_quote_limit, order_base_quote]:
            self.assertEqual(o.amount_base, amount_base, o.admin_comment)
            self.assertEqual(o.amount_quote, amount_quote, o.admin_comment)
            self.assertEqual(o.limit_rate, limit_rate, o.admin_comment)

    def _fluctuate_order_amount(self, order):
        order.amount_base *= Decimal('2')
        order.amount_quote *= Decimal('4')
        order.save()

    @patch(SCRYPT_ROOT + '_get_tx')
    @patch(SCRYPT_ROOT + '_get_txs')
    def _pay_for_order(self, order, scrypt_txs, scrypt_tx):
        scrypt_txs.return_value = self.get_scrypt_tx(
            order.deposit_amount,
            order.deposit_address.address
        )
        amount_quote = order.amount_quote
        amount_base = order.amount_base
        self._fluctuate_order_amount(order)
        import_transaction_deposit_scrypt_invoke.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.amount_quote, amount_quote)
        self.assertEqual(order.amount_base, amount_base)
        self.assertEqual(order.status, order.PAID_UNCONFIRMED)
        self.assertEqual(order.book_status, order.NEW)
        scrypt_tx.return_value = {
            'confirmations': 0
        }
        update_pending_transactions_invoke.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.book_status, order.NEW)
        scrypt_tx.return_value = {
            'confirmations':
                order.deposit_currency.min_order_book_confirmations
        }
        update_pending_transactions_invoke.apply_async()
        order.refresh_from_db()
        self.assertEqual(order.book_status, order.OPEN)
        tx = order.transactions.get(type=Transaction.DEPOSIT)
        self._check_order_transaction(order, tx)

    @patch(SCRYPT_ROOT + '_get_tx')
    def _set_as_paid_limit_orders(self, scrypt_tx):
        limit_orders = LimitOrder.objects.filter(
            status=LimitOrder.PAID_UNCONFIRMED
        )
        for order in limit_orders:
            error_msg = '{}'.format(order)
            scrypt_tx.return_value = {
                'confirmations':
                    order.deposit_currency.min_confirmations
            }
            update_pending_transactions_invoke.apply_async()
            order.refresh_from_db()
            if order.filled == Decimal('1'):
                self.assertEqual(order.book_status, LimitOrder.CLOSED,
                                 error_msg)
                self.assertEqual(order.status, order.PAID, error_msg)
            else:
                self.assertEqual(order.book_status, LimitOrder.OPEN, error_msg)
                self.assertEqual(order.status, order.PAID_UNCONFIRMED,
                                 error_msg)

    def _check_order_transaction(self, order, tx):
        _key = 'withdraw' if tx.type == tx.WITHDRAW else 'deposit'
        order_currency = getattr(order, '{}_currency'.format(_key))
        self.assertEqual(order_currency, tx.currency)
        order_amount = getattr(order, '{}_amount'.format(_key))
        self.assertEqual(order_amount, tx.amount)

    @patch(SCRYPT_ROOT + '_get_tx')
    @patch(SCRYPT_ROOT + 'get_info')
    @patch(SCRYPT_ROOT + 'release_coins')
    def _release_limit_orders(self, scrypt_release, scrypt_health, scrypt_tx):
        orders = LimitOrder.objects.filter(status=LimitOrder.PAID)
        scrypt_release.side_effect =\
            [(o.unique_reference, True) for o in orders]
        scrypt_health.return_value = {}
        min_confs = max(
            [o.withdraw_currency.min_confirmations for o in orders]
        )
        scrypt_tx.return_value = {
            'confirmations':
                min_confs
        }
        exchange_order_release_periodic.apply_async()
        update_pending_transactions_invoke.apply_async()
        for order in orders:
            error_msg = '{}'.format(order)
            self.assertTrue(order.coverable)
            order.refresh_from_db()
            self.assertEqual(order.status, order.COMPLETED, error_msg)
            tx = order.transactions.get(type=Transaction.WITHDRAW)
            self._check_order_transaction(order, tx)

    def test_create_trade(self):
        bid_high = Decimal('10e-7')
        ask = bid = Decimal('9e-7')
        assert ask < bid_high
        buy_order = self._create_limit_order_api(
            order_type=LimitOrder.BUY,
            amount_base=Decimal('10000'),
            limit_rate=bid_high,
        )
        self.assertEqual(buy_order.withdraw_address.address, self.doge_address)
        self.assertEqual(buy_order.refund_address.address,
                         self.btc_refund_address)
        self.assertEqual(
            buy_order.deposit_address.currency,
            buy_order.refund_address.currency
        )
        self.assertEqual(buy_order.filled, Decimal('0'))

        self._pay_for_order(buy_order)
        sell_order = self._create_limit_order_api(
            order_type=LimitOrder.SELL,
            amount_base=Decimal('11000'),
            limit_rate=ask,
        )
        self.assertEqual(sell_order.withdraw_address.address, self.btc_address)
        self.assertEqual(sell_order.refund_address.address,
                         self.doge_refund_address)
        self.assertEqual(
            sell_order.deposit_address.currency,
            sell_order.refund_address.currency
        )
        self._pay_for_order(sell_order)
        trade1 = Trade.objects.get(buy_order=buy_order, sell_order=sell_order)
        self.assertEqual(
            trade1.amount_base,
            min(buy_order.amount_base, sell_order.amount_base)
        )
        buy_order.refresh_from_db()
        self.assertEqual(buy_order.filled, Decimal('1'))
        self.assertEqual(buy_order.book_status, LimitOrder.CLOSED)
        self.assertEqual(sell_order.filled,
                         trade1.amount_base / sell_order.amount_base)
        self.assertEqual(
            trade1.amount_quote,
            trade1.amount_base * max(sell_order.limit_rate,
                                     buy_order.limit_rate)
        )
        sell_order2 = self._create_limit_order_api(
            order_type=LimitOrder.SELL,
            amount_base=Decimal('900'),
            limit_rate=ask,
        )
        self.assertEqual(sell_order2.withdraw_address.address,
                         self.btc_address)
        self.assertEqual(sell_order2.refund_address.address,
                         self.doge_refund_address)
        self.assertEqual(
            sell_order2.deposit_address.currency,
            sell_order2.refund_address.currency
        )
        self._pay_for_order(sell_order2)
        buy_order2 = self._create_limit_order_api(
            order_type=LimitOrder.BUY,
            amount_base=Decimal('2000'),
            limit_rate=bid,
        )
        self.assertEqual(buy_order2.withdraw_address.address,
                         self.doge_address)
        self.assertEqual(buy_order2.refund_address.address,
                         self.btc_refund_address)
        self.assertEqual(
            buy_order2.deposit_address.currency,
            buy_order2.refund_address.currency
        )
        self._pay_for_order(buy_order2)
        sell_order.refresh_from_db()
        sell_order2.refresh_from_db()
        self.assertEqual(sell_order.filled, Decimal('1'))
        self.assertEqual(sell_order.book_status, LimitOrder.CLOSED)
        self.assertEqual(sell_order2.filled, Decimal('1'))
        self.assertEqual(sell_order2.book_status, LimitOrder.CLOSED)
        trade2 = Trade.objects.get(buy_order=buy_order2, sell_order=sell_order)
        self.assertEqual(trade2.sell_order, sell_order)
        self.assertEqual(trade2.buy_order, buy_order2)
        self.assertEqual(
            trade2.amount_base,
            min(
                abs(buy_order.amount_base - sell_order.amount_base),
                buy_order2.amount_base
            )
        )
        self.assertEqual(trade2.amount_quote,
                         trade2.amount_base * sell_order.limit_rate)
        trade3 = Trade.objects.get(buy_order=buy_order2,
                                   sell_order=sell_order2)
        self.assertEqual(
            buy_order2.filled,
            (trade2.amount_base + trade3.amount_base) / buy_order2.amount_base
        )
        self.assertEqual(
            trade3.amount_base,
            abs(
                sell_order.amount_base + sell_order2.amount_base -
                trade1.amount_base - trade2.amount_base
            )
        )
        self.assertEqual(trade3.amount_quote,
                         trade3.amount_base * sell_order.limit_rate)

        for o in LimitOrder.objects.filter(order_type=LimitOrder.SELL):
            _trades = o.sell_trades.all()
            expected_quote = sum([m.amount_quote for m in _trades])
            expected_base = sum([m.amount_base for m in _trades])
            self.assertEqual(o.closed_amount_base, expected_base)
            self.assertEqual(o.closed_amount_quote, expected_quote)
            self.assertAlmostEqual(o.rate, expected_quote / expected_base, 8)

        for o in LimitOrder.objects.filter(order_type=LimitOrder.BUY):
            _trades = o.buy_trades.all()
            expected_quote = sum([m.amount_quote for m in _trades])
            expected_base = sum([m.amount_base for m in _trades])
            self.assertEqual(o.closed_amount_base, expected_base)
            self.assertEqual(o.closed_amount_quote, expected_quote)
            self.assertAlmostEqual(o.rate, expected_quote / expected_base, 8)

        self._set_as_paid_limit_orders()
        self._release_limit_orders()

        # Check adress types
        for o in LimitOrder.objects.all():
            error_msg = '{}'.format(o)
            self.assertEqual(o.refund_address.type, Address.REFUND, error_msg)
            self.assertEqual(o.deposit_address.type, Address.DEPOSIT,
                             error_msg)
            self.assertEqual(o.withdraw_address.type, Address.WITHDRAW,
                             error_msg)

        order_book_obj = o.get_or_create_order_book(o.pair)
        self.order_book.refresh_from_db()
        self.assertEqual(order_book_obj.__str__(),
                         self.order_book.book_obj.__str__())
