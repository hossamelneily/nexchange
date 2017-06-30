import sys

from core.tests.utils import data_provider
from core.tests.utils import (create_payeer_mock_for_order,
                              get_payeer_mock, get_ok_pay_mock,
                              create_ok_payment_mock_for_order)
from orders.models import Order
from core.models import AddressReserve

from unittest.mock import patch
import requests_mock
from time import time
import json
from core.tests.test_ui.base import BaseTestUI
from payments.tests.base import BaseSofortAPITestCase
from core.tests.base import UPHOLD_ROOT


class TestUIFiatOrders(BaseTestUI, BaseSofortAPITestCase):

    @data_provider(lambda: (
       ([{'name': 'OK Pay', 'success_url': '/okpay'}, # noqa
         {'name': 'Payeer Wallet', 'success_url': '/payeer'}], True, True),
    ))
    def test_buy1(self, payment_methods, automatic_payment, do_logout):
        self.base_test_buy(payment_methods, automatic_payment, do_logout)

    @data_provider(lambda: (
        ([{'name': 'Alfa-Bank'}, {'name': 'Sberbank'},
          {'name': 'Sepa'}, {'name': 'Swift'}], False, False),
    ))
    def test_buy2(self, payment_methods, automatic_payment, do_logout):
        self.base_test_buy(payment_methods, automatic_payment, do_logout)

    @data_provider(lambda: (
        ([{'name': 'PayPal'}, {'name': 'Skrill'}], False, False),
        ([{'name': 'Visa'}], False, False),
        ([{'name': 'Qiwi Wallet', 'pair_name': 'BTCRUB'}], False, False),
    ))
    def test_buy3(self, payment_methods, automatic_payment, do_logout):
        self.base_test_buy(payment_methods, automatic_payment, do_logout)

    @data_provider(lambda: (
        ([{'name': 'Sofort', 'success_url': '/sofort'}], True, True),
    ))
    def test_buy4(self, payment_methods, automatic_payment, do_logout):
        self.base_test_buy(payment_methods, automatic_payment, do_logout)

    def base_test_buy(self, payment_methods, automatic_payment, do_logout):
        self.workflow = 'BUY'
        for payment_method in payment_methods:
            self.screenshot_no = 1
            self.payment_method = self.screenpath2 = payment_method['name']
            print('Test {}'.format(self.payment_method))
            pair_name = payment_method.get('pair_name', 'BTCEUR')
            try:
                self.checkbuy(pair_name)
                if automatic_payment:
                    success_url = '/payments/success{}'.format(
                        payment_method['success_url']
                    )
                    self.automatic_checkout(
                        success_url=success_url
                    )
            except Exception as e:
                print(self.payment_method + " " + str(e))
                sys.exit(1)
            if do_logout:
                self.logout()

    @data_provider(lambda: (
        (['PayPal',
          'Qiwi Wallet',
          'OK Pay'], 'BTCRUB'),
    ))
    def test_sell1(self, payment_methods, pair_name):
        self.base_test_sell(payment_methods, pair_name=pair_name)

    @data_provider(lambda: (
        (['Skrill',
          'Card 2 Card',
          'Sepa',
          'Swift'],),
    ))
    def test_sell2(self, payment_methods):
        self.base_test_sell(payment_methods)

    def base_test_sell(self, payment_methods, pair_name='BTCEUR',
                       do_logout=False):
        self.workflow = 'SELL'
        print('Test sell')
        self.currency_code = 'BTC'
        for payment_method in payment_methods:
            self.screenshot_no = 1
            self.payment_method = self.screenpath2 = payment_method
            try:
                self.checksell(pair_name=pair_name)
            except Exception as e:
                print(self.payment_method + " " + str(e))
                sys.exit(1)
            if do_logout:
                self.logout()

    def checkbuy(self, pair_name='BTCEUR'):
        order_type = 'BUY'
        self.request_order(order_type, pair_name=pair_name)

        if not self.logged_in:
            self.login_phone()
        # FIXME: this fails on test pipeline
        # self.check_confirm_amounts()
        # press buy
        self.place_order(order_type)

    @requests_mock.mock()
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch(UPHOLD_ROOT + 'get_transactions')
    @patch('orders.utils.send_money')
    def checksell(self, mock, send_money, get_txs, get_rtx,
                  pair_name='BTCEUR'):
        order_type = 'SELL'
        send_money.return_value = True
        self.request_order(order_type, pair_name=pair_name)
        modal = self.driver.find_element_by_xpath(
            '//div[@class="modal fade add_payout_method in"]'
        )
        if self.payment_method == 'Qiwi Wallet':
            self.fill_sell_card_data(modal, 'phone', self.phone)
        elif self.payment_method in ['OK Pay', 'PayPal', 'Skrill']:
            self.fill_sell_card_data(modal, 'iban', self.name)
            self.fill_sell_card_data(modal, 'account-number', self.email)
        elif self.payment_method in ['Card 2 Card', 'Sepa', 'Swift']:
            if self.payment_method == 'Card 2 Card':
                account = self.card_number
            elif self.payment_method == 'Swift':
                account = self.swift_iban
            else:
                account = self.account
            self.fill_sell_card_data(modal, 'account-number', account)
            if self.payment_method == 'Card 2 Card':
                self.fill_sell_card_data(modal, 'owner', self.name)
            else:
                self.fill_sell_card_data(modal, 'iban', self.name)
            if self.payment_method == 'Swift':
                self.fill_sell_card_data(modal, 'account-bic', self.bic)

        self.do_screenshot('Payment preference filled')

        card_go = modal.find_element_by_class_name('save-card')
        card_go.click()
        # login
        if not self.logged_in:
            self.login_phone()
        order_data = self.check_confirm_amounts()
        amount_base = order_data['amount_base']
        currency_base_code = order_data['currency_base']
        # end login
        self.mock_import_transaction(amount_base, currency_base_code,
                                     get_txs, get_rtx)

        self.place_order(order_type)
        # FIXME: should be COMPLETED after sell_order_release task changes
        self.check_order_status(Order.COMPLETED)
        self.check_sell_order_on_list()

    def mock_sell_transactions_from_customer(self, amount_base, mock,
                                             reserve_txs, import_txs):
        self.tx_id_api = 'tx' + str(time())
        reserve_txs.return_value = json.loads(self.completed)
        card = AddressReserve.objects.get(
            user__profile__phone=self.phone,
            currency=self.currency_code
        )
        get_txs_response = self.uphold_import_transactions_empty.format(
            tx_id_api1=self.tx_id_api,
            tx_id_api2='nonsense',
            amount1=amount_base,
            amount2='0.0',
            currency=card.currency,
            card_id=card.card_id,
        )
        import_txs.return_value = json.loads(get_txs_response)

    def check_sell_order_on_list(self):
        self.click_go_to_order_list()
        self.check_paid_toggle()
        self.check_order_status_indicator('released')
        self.do_screenshot('Payment Success')
        self.check_order_status_indicator('completed')

    def fill_sell_card_data(self, modal, class_name, value):
        key = modal.find_element_by_class_name(class_name)
        key.clear()
        key.send_keys(value)

    @requests_mock.mock()
    @patch(UPHOLD_ROOT + 'get_reserve_transaction')
    @patch('nexchange.utils.OkPayAPI._get_transaction_history')
    def automatic_checkout(self, mock, trans_history, reserve_txn,
                           success_url=None):
        trans_history.return_value = get_ok_pay_mock(
            data='transaction_history'
        )
        reserve_txn.return_value = {'status': 'completed'}
        mock.post('https://payeer.com/ajax/api/api.php',
                  text=get_payeer_mock('transaction_history'))
        method = self.order.payment_preference.payment_method
        if 'okpay' in method.name.lower():
            trans_history.return_value = create_ok_payment_mock_for_order(
                self.order
            )
        elif 'payeer' in method.name.lower():
            mock.post('https://payeer.com/ajax/api/api.php',
                      text=create_payeer_mock_for_order(self.order))
        elif 'sofort' in method.name.lower():
            transaction_data = {
                'order_id': self.order.unique_reference,
                'amount': self.order.amount_quote,
                'currency': self.order.pair.quote.code,
                'transaction_id': str(time())
            }
            transaction_xml = self.create_transaction_xml(
                **transaction_data
            )
            self.mock_transaction_history(mock, transaction_xml)
        self.do_screenshot('Before push auto-checkout')
        auto_checkout = self.driver.find_elements_by_class_name(
            'automatic-checkout'
        )
        self.assertTrue(
            auto_checkout,
            'There is no Automatic checkout button for {}'.format(
                self.payment_method
            )
        )
        # Payment success
        self.get_repeat_on_timeout(self.url + success_url)
        self.check_paid_toggle()
        self.do_screenshot('Payment Success')
        url_params = self.get_url_params(self.driver.current_url)
        self.assertEqual(
            url_params['is_paid'], 'true',
            'Success call from payment provider should send is_paid=true')
        self.assertEqual(
            url_params['oid'], self.order.unique_reference,
            'Success call from payment provider should send'
            ' oid={self.order.unique_reference} - current order.')
        self.check_order_status(Order.PAID)
        # Add withdraw address
        self.add_withdraw_address_on_payment_success()
        # Order must be released after adding withdraw address
        self.check_order_status_indicator('released', refresh=True)
        # Order completed then transaction is completed
        self.do_screenshot('Order Completed')
        self.check_order_status_indicator('completed')
