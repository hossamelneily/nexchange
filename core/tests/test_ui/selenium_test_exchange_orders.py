from core.tests.utils import data_provider
from orders.models import Order

from unittest.mock import patch
from core.tests.test_ui.base import BaseTestUI
from core.tests.base import UPHOLD_ROOT

from selenium.webdriver.common.by import By


class TestUIExchangeOrders(BaseTestUI):

    def setUp(self):
        super(TestUIExchangeOrders, self).setUp()
        self.BTC_address = '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'
        self.LTC_address = 'LUZ7mJZ8PheQVLcKF5GhitGuzZcgPWDPA4'
        self.ETH_address = '0x77454e832261aeed81422348efee52d5bd3a3684'
        self.DOGE_address = 'D6BpZ4pP17JDsjpSWVrB2Hpa4oCi5mLfua'

    @data_provider(lambda: (('ETHLTC', True),),)
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_tx')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_txs')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_release_exchange_order1(self, pair_name, do_logout, reserve_txs,
                                     import_txs, get_txs_scrypt,
                                     get_tx_scrypt):
        self.base_test_release_exchange_order(pair_name, do_logout,
                                              reserve_txs, import_txs,
                                              get_txs_scrypt, get_tx_scrypt)

    @data_provider(lambda: (('BTCETH', False),),)
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_tx')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_txs')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_release_exchange_order2(self, pair_name, do_logout, reserve_txs,
                                     import_txs, get_txs_scrypt,
                                     get_tx_scrypt):
        self.base_test_release_exchange_order(pair_name, do_logout,
                                              reserve_txs, import_txs,
                                              get_txs_scrypt, get_tx_scrypt)

    @data_provider(lambda: (('LTCBTC', False),),)
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_tx')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_txs')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_release_exchange_order3(self, pair_name, do_logout, reserve_txs,
                                     import_txs, get_txs_scrypt,
                                     get_tx_scrypt):
        self.base_test_release_exchange_order(pair_name, do_logout,
                                              reserve_txs, import_txs,
                                              get_txs_scrypt, get_tx_scrypt)

    @data_provider(lambda: (('LTCDOGE', False),),)
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_tx')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_txs')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_release_exchange_order4(self, pair_name, do_logout, reserve_txs,
                                     import_txs, get_txs_scrypt,
                                     get_tx_scrypt):
        self.base_test_release_exchange_order(pair_name, do_logout,
                                              reserve_txs, import_txs,
                                              get_txs_scrypt, get_tx_scrypt)

    @data_provider(lambda: (('DOGEBTC', False),),)
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_tx')
    @patch('nexchange.api_clients.rpc.ScryptRpcApiClient._get_txs')
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    def test_release_exchange_order5(self, pair_name, do_logout, reserve_txs,
                                     import_txs, get_txs_scrypt,
                                     get_tx_scrypt):
        self.base_test_release_exchange_order(pair_name, do_logout,
                                              reserve_txs, import_txs,
                                              get_txs_scrypt, get_tx_scrypt)

    def base_test_release_exchange_order(self, pair_name, do_logout, get_txs,
                                         get_rtx, get_txs_scrypt,
                                         get_tx_scrypt):
        pair_name = pair_name
        self.workflow = '{}'.format(pair_name)
        self.payment_method = '{}'.format(pair_name)
        self.screenshot_no = 1
        self.request_order(click_payment_icon=False, pair_name=pair_name)
        self.do_screenshot('After order request')
        if not self.logged_in:
            self.login_email()

        order_data = self.check_confirm_amounts(pair_name=pair_name)
        amount_quote = order_data['amount_quote']
        currency_quote_code = order_data['currency_quote']
        currency_base_code = order_data['currency_base']
        mock_currency_code = currency_quote_code
        mock_amount = amount_quote
        withdraw_currency_code = currency_base_code
        self.mock_import_transaction(mock_amount, mock_currency_code,
                                     get_txs, get_rtx, get_txs_scrypt,
                                     get_tx_scrypt)
        self.place_order()
        self.click_go_to_order_list()
        self.do_screenshot('After pres GO/GET coins')
        self.check_order_status(Order.PAID)
        self.check_paid_toggle()
        self.withdraw_address = getattr(
            self, '{}_address'.format(withdraw_currency_code)
        )

        self.add_withdraw_address_on_payment_success(add_new=True)
        self.do_screenshot('After add Withdraw Addrress')

        # All completed orders go in the expired/completed orders list.
        # Must open the list before checking order status indicator.
        self.click_element_by_name('Show expired and released',
                                   by=By.XPATH, screenshot=True)

        # Order must be released after adding withdraw address
        self.check_order_status_indicator('released', refresh=True)

        # Order completed then transaction is completed
        self.do_screenshot('Order Completed')
        self.check_order_status_indicator('completed')
        if do_logout:
            self.logout()
