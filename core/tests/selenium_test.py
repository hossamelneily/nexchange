import os
import sys
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from core.tests.base import TransactionImportBaseTestCase
from ticker.tests.base import TickerBaseTestCase
from core.tests.utils import data_provider
from selenium.webdriver.common.keys import Keys
from core.tests.utils import (create_payeer_mock_for_order,
                              get_payeer_mock, get_ok_pay_mock,
                              create_ok_payment_mock_for_order)
from orders.models import Order
from django.conf import settings
from django.contrib.auth.models import User
from core.models import Address

from accounts.models import SmsToken
from unittest.mock import patch
import requests_mock
from time import time


class TestUI(StaticLiveServerTestCase, TransactionImportBaseTestCase,
             TickerBaseTestCase):

    def setUp(self):
        super(TestUI, self).setUp()
        self.workflow = 'generic'
        self.phone = '+37068644145'
        self.email = 'sarunas@onin.ws'
        self.name = 'Sir Testalot'
        self.account = 'LT121000011101001000'
        self.card_number = '1234567887654321'
        self.bic = '123456'
        self.withdraw_address = '2NGBPxkKAevijTQFxp4WMwCjZYsFjqDMZ97'
        self.issavescreen = False
        self.url = self.live_server_url
        self.screenpath = os.path.join(
            os.path.dirname(__file__), 'Screenshots', str(time()))
        self.mkdir(self.screenpath)
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64)' \
                     ' AppleWebKit/537.36 (KHTML, like Gecko)' \
                     ' Chrome/37.0.2062.120 Safari/537.36'
        self.dcap = dict(DesiredCapabilities.PHANTOMJS)
        self.dcap["phantomjs.page.settings.userAgent"] = user_agent
        self.timeout = 30
        executable_path = os.path.join(
            settings.BASE_DIR, 'node_modules/.bin/phantomjs')
        self.driver = webdriver.PhantomJS(
            executable_path=executable_path,
            service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any'],
            desired_capabilities=self.dcap)
        self.driver.set_window_size(1400, 1000)
        self.driver.set_page_load_timeout(self.timeout / 3)
        self.wait = WebDriverWait(self.driver, self.timeout)
        self.payment_method = None
        self.screenshot_overall_no = 1
        self.stamp = time()
        self.shot_base64 = None

    def tearDown(self):
        super(TestUI, self).tearDown()
        self.driver.close()

    @data_provider(lambda: (
       ([{'name': 'OK Pay', 'success_url': '/okpay'}, # noqa
         {'name': 'Payeer Wallet', 'success_url': '/payeer'}], True),
       ([{'name': 'Alfa-Bank'}, {'name': 'Sberbank'},
         {'name': 'Sepa'}, {'name': 'Swift'}], False),
       ([{'name': 'Qiwi Wallet'},
         {'name': 'PayPal'}, {'name': 'Skrill'}], False),
       ([{'name': 'Visa'}, {'name': 'Mastercard'}], False),
    ))
    def test_buy(self, payment_methods, automatic_payment):
        self.workflow = 'BUY'
        for payment_method in payment_methods:
            self.screenshot_no = 1
            self.payment_method = payment_method['name']
            self.driver.delete_all_cookies()
            print('Test {}'.format(self.payment_method))
            try:
                self.checkbuy()
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

    @data_provider(lambda: (
        (['PayPal',
          'OK Pay',
          # 'Qiwi wallet',
          'Skrill',
          # 'Card 2 Card',
          'Sepa',
          'Swift'],),
    ))
    def test_sell(self, payment_methods):
        self.workflow = 'SELL'
        print('Test sell')
        for payment_method in payment_methods:
            self.screenshot_no = 1
            self.payment_method = payment_method
            self.driver.delete_all_cookies()
            try:
                self.checksell()
            except Exception as e:
                print(self.payment_method + " " + str(e))
                sys.exit(1)

    def get_repeat_on_timeout(self, url):
        repeat = 5
        for i in range(1, repeat + 1):
            if i == repeat:
                self.driver.get(url)
                break
            try:
                self.driver.get(url)
            except TimeoutException:
                continue
            else:
                break
        # sleep for page load
        sleep(self.timeout / 10)

    def mkdir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def click_span(self, class_name):
        btnes = self.driver.find_elements_by_class_name(class_name)
        for btsendsms in btnes:
            if btsendsms.get_attribute('class') \
                    .find('btn-primary') > -1:
                btsendsms.click()
                break

    @requests_mock.mock()
    def login_phone(self, mock):
        mock.post(
            'https://www.google.com/recaptcha/api/siteverify',
            text='{\n "success": true\n}'
        )
        self._mock_cards_reserve(mock)
        self.do_screenshot('after check method click')
        # FIXME: 2 phones found
        self.wait.until(EC.element_to_be_clickable((
            By.XPATH,
            '//div[@id="menu2"]//div[@class="intl-tel-input allow-dropdown"]'
        )))

        phone = self.driver.find_element_by_class_name(
            'menu2').find_element_by_class_name('phone')
        phone.clear()
        phone.send_keys(self.phone)

        self.do_screenshot('after input phone number')
        self.click_span(class_name='create-acc')
        # input sms code

        self.wait.until(EC.element_to_be_clickable(
            (By.ID, 'verification_code')
        )).send_keys(
            SmsToken.objects.get(user__profile__phone=self.phone).sms_token
        )

        self.do_screenshot('after input code number')
        self.click_span(class_name='verify-acc')

        self.selenium_user = User.objects.get(username=self.phone)
        # FIXME: Should be done by mock
        sleep(self.timeout / 20)

    def request_order(self, order_type):
        print(self.payment_method)
        self.get_repeat_on_timeout(self.url)
        self.do_screenshot('main_')
        self.wait.until(EC.element_to_be_clickable((
            By.CLASS_NAME, 'trigger-{}'.format(order_type)))).click()
        self.do_screenshot('after {} click'.format(order_type))
        self.click_on_payment_icon()

    def place_order(self, order_type):
        bt_buys = self.driver.find_elements_by_class_name('{}-go'.format(
            order_type
        ))
        for b in bt_buys:
            if b.get_attribute('class') \
                    .find('place-order') > -1:
                b.click()
                break
        self.wait.until(EC.element_to_be_clickable((
            By.CLASS_NAME, 'unique_ref')))
        ref = self.driver.find_element_by_class_name('unique_ref').text
        self.order = Order.objects.get(unique_reference=ref)
        self.do_screenshot('End_')

    def checkbuy(self):
        order_type = 'buy'
        self.request_order(order_type)

        sleep(self.timeout / 20)
        self.login_phone()
        self.do_screenshot('after verifycate phone')
        # press buy
        self.place_order(order_type)

    @requests_mock.mock()
    @patch('orders.utils.send_money')
    def checksell(self, mock, send_money):
        order_type = 'sell'
        send_money.return_value = True
        self.request_order(order_type)
        sleep(self.timeout / 5)
        modal = self.driver.find_element_by_xpath(
            '//div[@class="modal fade sellMethModal in"]'
        )
        if self.payment_method == 'Qiwi wallet':
            self.fill_sell_card_data(modal, 'phone', self.phone)
        elif self.payment_method in ['Ok Pay', 'PayPal', 'Skrill']:
            self.fill_sell_card_data(modal, 'iban', self.name)
            self.fill_sell_card_data(modal, 'account-number', self.email)
        elif self.payment_method in ['Card 2 Card', 'Sepa', 'swift']:
            if self.payment_method == 'Card 2 Card':
                account = self.card_number
            else:
                account = self.account
            self.fill_sell_card_data(modal, 'account-number', account)
            self.fill_sell_card_data(modal, 'iban', self.name)
            if self.payment_method == 'swift':
                self.fill_sell_card_data(modal, 'account-bic', self.bic)

        self.do_screenshot('Payment preference filled')

        card_go = modal.find_element_by_class_name('save-card')
        card_go.click()
        # login
        sleep(0.8)
        self.login_phone()
        sleep(self.timeout / 5)
        self.do_screenshot('after login')
        # end login
        self.mock_sell_transactions_from_customer(mock)

        self.place_order(order_type)
        # FIXME: should be COMPLETED after sell_order_release task changes
        self.check_order_status(Order.COMPLETED)
        self.check_sell_order_on_list()

    def mock_sell_transactions_from_customer(self, mock):
        self.wait.until(EC.element_to_be_clickable((
            By.CLASS_NAME, 'btc-amount-confirm')))
        amount_base = self.driver.find_element_by_class_name(
            'btc-amount-confirm').text
        addresses = Address.objects.filter(type=Address.DEPOSIT)
        self.tx_id = 'tx' + str(time())
        url_txs = 'http://btc.blockr.io/api/v1/tx/info/{}'.format(self.tx_id)
        mock.get(url_txs, text=self.blockr_response_tx1)
        get_txs_response = (
            '{{"status": "success", "data": {{"txs": [{{"time_utc": '
            '"2016-08-11T16:33:24Z","tx": "{tx_id}","confirmations": 0,'
            '"amount": {amount},"amount_multisig": 0}}]}}}}'.format(
                tx_id=self.tx_id,
                amount=amount_base
            )
        )
        for address in addresses:
            url_addr = 'http://{}.blockr.io/api/v1/address/txs/{}'.format(
                address.currency.code.lower(), address.address
            )
            mock.get(url_addr, text=get_txs_response)

    def check_sell_order_on_list(self):
        try:
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@class="modal fade in"]//a')
            )).click()
        except TimeoutException:
            # FIXME: sometimes unclickable is clicked (if you get there and
            # tests are still passing)
            self.do_screenshot('TIMEOUT on click GO sell (tests should not '
                               'PASS cause you should not be abble to click '
                               'unclickable element)')
        self.check_paid_toggle()
        self.check_order_status_indicator('released')
        self.do_screenshot('Payment Success')
        self.check_order_status_indicator('completed')

    def fill_sell_card_data(self, modal, class_name, value):
        key = modal.find_element_by_class_name(class_name)
        key.clear()
        key.send_keys(value)

    def click_on_payment_icon(self):
        try:
            self._click_on_payment_icon()
        except TimeoutException:
            self.do_screenshot('Tiemout Exception')
            sleep(self.timeout / 2)
            try:
                self._click_on_payment_icon()
            except TimeoutException:
                raise TimeoutException(
                    '{} icon not not loaded.url:{}src: {}'.format(
                        self.payment_method, self.driver.current_url,
                        self.driver.page_source
                    )
                )

    def _click_on_payment_icon(self):
        self.do_screenshot('Before click on Payment Icon')
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             '//div[@class="modal fade in"]//div[@data-label="{}"]'.format(
                 self.payment_method
             ))
        )).click()

    @requests_mock.mock()
    @patch('nexchange.utils.api.get_reserve_transaction')
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
        self.check_order_status_indicator('released')
        # Order completed then transaction is completed
        self.do_screenshot('Order Completed', refresh=True)
        self.check_order_status_indicator('completed')

    def check_paid_toggle(self):
        self.driver.refresh()
        self.do_screenshot('Before payment Toggler check')
        success_toggle_input = self.select_paid_toggle()
        if len(success_toggle_input) == 0:
            self.driver.refresh()
            sleep(self.timeout / 10)
            success_toggle_input = self.select_paid_toggle()
        self.assertTrue(
            len(success_toggle_input) >= 1,
            'Order is not marked as paid after auto_checkout '
            'redirect to success_url. ({}). src:{}'.format(
                self.payment_method,
                self.driver.page_source
            )
        )

    def select_paid_toggle(self):
        res = []
        res = self.driver.find_elements_by_xpath(
            '//div[@class="toggle btn btn-success"]//input[@data-pk="{'
            '}"]'.format(self.order.pk)
        )
        return res

    def get_url_params(self, url):
        res = {}
        url_split = url.split('?')
        if len(url_split) == 2:
            params = url_split[1].split('&')
            for param in params:
                p = param.split('=')
                res.update({p[0]: p[1]})
        return res

    def write_withdraw_address_on_popover(self):
        popover_path = '//div[@class="popover fade top in"]'
        create_path = (
            '//div[contains(@class, "create_withdraw_address")]'
            '//input[@type="text"]'
        )
        option_path = (
            '//div[contains(@class, "set_withdraw_address")]'
            '//option'
        )
        submit_path = '//button[@type="submit"]'
        create = self.driver.find_element_by_xpath(popover_path + create_path)
        submit = self.driver.find_element_by_xpath(popover_path + submit_path)
        options = self.driver.find_elements_by_xpath(popover_path +
                                                     option_path)
        if create.is_displayed():
            create.click()
            create.send_keys(self.withdraw_address)
            create.send_keys(Keys.ENTER)
        else:
            # First[0] option is placeholder
            options[1].click()
            submit.click()

    @patch('nexchange.utils.api.execute_txn')
    @patch('nexchange.utils.api.prepare_txn')
    def add_withdraw_address_on_payment_success(self, prepare_txn,
                                                execute_txn):
        prepare_txn.return_value = 'txid{}'.format(self.order.unique_reference)
        execute_txn.return_value = True
        address = self.driver.find_element_by_id(
            'span-withdraw-{}'.format(self.order.pk)
        )
        address.click()
        self.write_withdraw_address_on_popover()
        sleep(self.timeout / 5)
        self.do_screenshot('Withdraw Address added')

    def check_order_status(self, status):
        for _ in range(3):
            self.order.refresh_from_db()
            if self.order.status != status:
                sleep(self.timeout / 6)
            else:
                break
        self.assertEqual(
            self.order.status, status,
            'Bad Order status on {}'.format(self.payment_method))

    def check_order_status_indicator(self, indicator_name, checked=True):
        self.driver.refresh()
        is_checked = 'fa fa-check fa-1'
        is_unchecked = 'fa fa-close fa-1 red'
        if checked:
            use = is_checked
        else:
            use = is_unchecked
        path = (
            '//span[@class="{}-indicator order-{}"]//span[@class="{}"]'.format(
                indicator_name, self.order.pk, use
            )
        )
        indicator = []
        for _ in range(5):
            indicator = self.driver.find_elements_by_xpath(path)
            if len(indicator) == 0:
                self.driver.refresh()
                continue
            break
        self.assertNotEqual(
            len(indicator), 0,
            '{} order is not checked as {}'.format(
                self.payment_method, indicator_name
            )
        )

    def do_screenshot(self, filename, refresh=False):
        self.shot_base64 = self.driver.get_screenshot_as_base64()
        now = time()
        diff = now - self.stamp
        self.stamp = now
        if self.issavescreen:
            if refresh:
                self.driver.refresh()
            if self.payment_method is None:
                method_path = 'unsorted'
            else:
                method_path = self.payment_method
            path = os.path.join(
                self.screenpath, self.workflow, method_path)
            filename = '{}({}). {} ({:.2f}s)'.format(
                self.screenshot_no, self.screenshot_overall_no, filename, diff
            )
            self.mkdir(path)
            self.driver.get_screenshot_as_file(
                os.path.join(path, filename + '.png'))
            self.screenshot_no += 1
            self.screenshot_overall_no += 1
