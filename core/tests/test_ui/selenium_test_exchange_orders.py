from core.tests.utils import data_provider
from orders.models import Order

from unittest.mock import patch
from core.tests.test_ui.base import BaseTestUI


class TestUIExchangeOrders(BaseTestUI):

    def setUp(self):
        super(TestUIExchangeOrders, self).setUp()
        self.BTC_address = '1GR9k1GCxJnL3B5yryW8Kvz7JGf31n8AGi'
        self.LTC_address = 'LYUoUn9ATCxvkbtHseBJyVZMkLonx7agXA'
        self.ETH_address = '0x8116546AaC209EB58c5B531011ec42DD28EdFb71'

    @data_provider(
        lambda: (('ETHLTC', Order.BUY, True),
                 ('ETHLTC', Order.SELL, False),
                 ('BTCETH', Order.BUY, False),
                 ('BTCETH', Order.SELL, False),
                 ('BTCLTC', Order.BUY, False),
                 ('BTCLTC', Order.SELL, False),
                 )
    )
    @patch('nexchange.utils.api.get_card_transactions')
    @patch('nexchange.utils.api.get_reserve_transaction')
    def test_release_exchange_order(self, pair_name, order_type, do_logout,
                                    reserve_txs, import_txs):
        self.workflow = '{}'.format(pair_name)
        order_type_display = 'BUY' if order_type == Order.BUY else 'SELL'
        self.screenpath2 = order_type_display
        self.payment_method = '{}-{}'.format(
            pair_name, order_type_display
        )
        self.screenshot_no = 1
        self.request_order(order_type_display, click_payment_icon=False,
                           pair_name=pair_name)
        self.do_screenshot('After order request')
        if not self.logged_in:
            self.login_phone()
        order_data = self.check_confirm_amounts(pair_name=pair_name)
        amount_base = order_data['amount_base']
        amount_quote = order_data['amount_quote']
        currency_quote_code = order_data['currency_quote']
        currency_base_code = order_data['currency_base']
        if order_type == Order.BUY:
            mock_currency_code = currency_quote_code
            mock_amount = amount_quote
            withdraw_currency_code = currency_base_code
        elif order_type == Order.SELL:
            mock_currency_code = currency_base_code
            mock_amount = amount_base
            withdraw_currency_code = currency_quote_code
        self.mock_import_transaction(mock_amount, mock_currency_code,
                                     reserve_txs, import_txs)
        self.place_order(order_type_display)
        self.click_go_to_order_list()
        self.do_screenshot('After pres GO/GET coins')
        self.check_order_status(Order.PAID)
        self.check_paid_toggle()
        self.withdraw_address = getattr(
            self, '{}_address'.format(withdraw_currency_code)
        )
        self.add_withdraw_address_on_payment_success(add_new=True)
        self.do_screenshot('After add Withdraw Addrress')
        # Order must be released after adding withdraw address
        self.check_order_status_indicator('released')
        # Order completed then transaction is completed
        self.do_screenshot('Order Completed', refresh=True)
        self.check_order_status_indicator('completed')
        if do_logout:
            self.logout()
