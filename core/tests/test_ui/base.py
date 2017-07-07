import os
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
from selenium.webdriver.common.keys import Keys
from orders.models import Order
from core.models import AddressReserve
from verification.models import Verification
from django.conf import settings
from django.contrib.auth.models import User

from accounts.models import SmsToken
from unittest.mock import patch
import requests_mock
from time import time
import json
from random import randint
from core.tests.base import UPHOLD_ROOT


class BaseTestUI(StaticLiveServerTestCase, TransactionImportBaseTestCase,
                 TickerBaseTestCase):

    def setUp(self):
        super(BaseTestUI, self).setUp()
        self.workflow = self.__class__.__name__.split('TestUI')[1].upper()
        self.screenpath2 = self._testMethodName.split('test_')[1].upper()
        self.phone = '+37068644245'
        self.email = 'sarunas@onin.ws'
        self.name = 'Sir Testalot'
        self.account = 'LT121000011101001000'
        self.card_number = '1234567887654321'
        self.swift_iban = '987654321'
        self.bic = 'DABAIE2D'
        self.withdraw_address = '162hFhCaEwDbBKbwLaUyAHhd4aVB3yW7DJ'
        self.issavescreen = True
        self.url = self.live_server_url
        local_root_path = '{}_{}'.format(int(time()), self._testMethodName)
        self.screenpath = os.path.join(
            os.path.dirname(__file__), 'Screenshots', local_root_path)
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
        self.screenshot_overall_no = self.screenshot_no = 1
        self.stamp = time()
        self.shot_base64 = None
        self.logged_in = False
        self.recursive_withdraw_calls = 0
        self.xpath_query_contains_text = "//*[contains(text(), '{}')]"
        from decimal import Decimal
        from ticker.models import Ticker
        tickers = Ticker.objects.all()
        for ticker in tickers:
            ticker.ask = ticker.bid = Decimal('10000')
            ticker.save()

    def tearDown(self):
        super(BaseTestUI, self).tearDown()
        self.driver.close()

    def get_repeat_on_timeout(self, url):
        repeat = 5
        for i in range(1, repeat + 1):
            if i == repeat:
                self.driver.get(url)
                break
            try:
                self.driver.get(url)
            except TimeoutException:
                self.do_screenshot('Smth wrong with url load')
                self.do_screenshot('Smth wrong with url load, refresh',
                                   refresh=True)
                continue
            else:
                break
        # sleep for page load
        self.wait_page_load()

    def get_currency_pair_main_screen(self, pair_name, lang='en'):
        url = '{}/{}/orders/buy_bitcoin/{}/'.format(self.url, lang,
                                                    pair_name)
        self.get_repeat_on_timeout(url)

    def mkdir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def click_span(self, class_name, second_class='btn-primary'):
        btnes = self.driver.find_elements_by_class_name(class_name)
        for btn in btnes:
            if btn.get_attribute('class') \
                    .find(second_class) > -1:
                if btn.is_displayed():
                    btn.click()
                    break

    def logout(self):
        self.driver.delete_all_cookies()
        self.logged_in = False

    def fill_element_by_id(self, element_id, value):
        element = self.driver.find_element_by_id(element_id)
        element.clear()
        element.send_keys(value)
        self.do_screenshot('after fill element:{}, with value:{}'.format(
            element_id, value
        ))

    def wait_until_clickable_element_by_name(
            self, name, by=By.CLASS_NAME, screenshot=False,
            xpath_query=None):

        if xpath_query is None:
            xpath_query = self.xpath_query_contains_text
        if by == By.XPATH:
            query = xpath_query.format(name)
        else:
            query = name
        element = self.wait.until(
            EC.element_to_be_clickable((by, query))
        )
        if screenshot:
            self.do_screenshot('element: {} is clickable'.format(name))
        return element

    def click_element_by_name(self, name, by=By.CLASS_NAME,
                              screenshot=False, xpath_query=None):
        self.wait_until_clickable_element_by_name(
            name, by, xpath_query=xpath_query).click()
        if screenshot:
            self.do_screenshot('after click on: {}'.format(name))

    @requests_mock.mock()
    def otp_login(self, username, mock):
        mock.post(
            'https://www.google.com/recaptcha/api/siteverify',
            text='{\n "success": true\n}'
        )
        self.get_repeat_on_timeout(self.url)
        self.click_element_by_name('Login', by=By.XPATH)
        self.fill_element_by_id('id_username', username)
        self.click_element_by_name('send-otp')
        self.wait_until_clickable_element_by_name('login-otp')
        token = SmsToken.objects.get(user__username=username).sms_token
        self.fill_element_by_id('id_password', token)
        self.click_element_by_name('login-otp')
        self.wait_until_clickable_element_by_name('trigger-buy')
        self.selenium_user = User(username=username)

    def login_phone(self):
        self.login_seemless()

    def login_email(self):
        self.login_seemless(with_email=True)

    @requests_mock.mock()
    def login_seemless(self, mock, with_email=False):
        mock.post(
            'https://www.google.com/recaptcha/api/siteverify',
            text='{\n "success": true\n}'
        )
        self._mock_cards_reserve(mock)
        self.do_screenshot('after check method click')
        # FIXME: try wait for smth instead of sleep
        sleep(1)

        if with_email:
            account_input = self.driver.find_element_by_class_name(
                'menu2').find_element_by_class_name('email')
            self.username = self.email
        else:
            self.click_span(class_name='switch-login',
                            second_class='email-verification')
            self.wait.until(EC.element_to_be_clickable((
                By.XPATH,
                '//div[@id="menu2"]//'
                'div[@class="intl-tel-input allow-dropdown"]'
            )))
            account_input = self.driver.find_element_by_class_name(
                'menu2').find_element_by_class_name('phone')
            self.do_screenshot('switched login')
            self.username = self.phone

        account_input.clear()
        account_input.send_keys(self.username)

        self.do_screenshot('after input {}'.format(
            'email' if with_email else 'phone'
        ))

        if not with_email:
            self.click_span(class_name='create-acc')
        else:
            self.click_span(class_name='create-acc',
                            second_class='email-verification')

        self.wait.until(EC.element_to_be_clickable(
            (By.ID, 'verification_code')
        )).send_keys(
            SmsToken.objects.get(user__username=self.username).sms_token
        )

        self.do_screenshot('after input code number')
        self.click_span(class_name='verify-acc')

        self.selenium_user = User.objects.get(username=self.username)
        if not self.selenium_user.profile.is_verified:
            Verification(user=self.selenium_user, id_status=Verification.OK,
                         util_status=Verification.OK).save()
        sleep(self.timeout / 60)
        self.do_screenshot('After Login')
        self.logged_in = True

    def wait_page_load(self, delay=None):
        if delay is not None:
            sleep(delay)
        state = self.driver.execute_script(
            'return document.readyState;')
        if state == 'complete':
            return
        else:
            sleep(self.timeout / 60)
            self.wait_page_load()

    def request_order(self, order_type, click_payment_icon=True,
                      pair_name=None):
        print(self.payment_method)
        order_type = order_type.lower()
        if pair_name is None:
            self.get_repeat_on_timeout(self.url)
        else:
            self.get_currency_pair_main_screen(pair_name)
        self.do_screenshot('main_')
        self.wait.until(EC.element_to_be_clickable((
            By.CLASS_NAME, 'trigger-{}'.format(order_type)))).click()
        self.do_screenshot('after {} click'.format(order_type))
        if click_payment_icon:
            self.click_on_payment_icon()

    def place_order(self, order_type):
        order_type = order_type.lower()
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

    def click_on_payment_icon(self):
        try:
            self._click_on_payment_icon()
        except TimeoutException:
            self.do_screenshot('Tiemout Exception')
            sleep(self.timeout / 20)
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

    def check_paid_toggle(self):
        self.do_screenshot('Before payment Toggle check')
        success_toggle_input = self.select_paid_toggle()
        if len(success_toggle_input) == 0:
            self.do_screenshot('Check for toggle once again', refresh=True)
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

    def write_withdraw_address_on_popover(self, add_new=False):
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
        add_path = '//button[@type="button"]'
        create = self.driver.find_element_by_xpath(popover_path + create_path)
        submit = self.driver.find_element_by_xpath(popover_path + submit_path)
        add = self.driver.find_element_by_xpath(popover_path + add_path)
        options = self.driver.find_elements_by_xpath(popover_path +
                                                     option_path)
        if create.is_displayed():
            create.click()
            create.send_keys(self.withdraw_address)
            create.send_keys(Keys.ENTER)
        elif add_new:
            try:
                add.click()
            except TimeoutException as e:
                raise TimeoutException('{}: {}'.format(self.payment_method, e))
            create.click()
            create.send_keys(self.withdraw_address)
            create.send_keys(Keys.ENTER)
        else:
            # First[0] option is placeholder
            options[1].click()
            submit.click()

    @patch(UPHOLD_ROOT + 'execute_txn')
    @patch(UPHOLD_ROOT + 'prepare_txn')
    def add_withdraw_address_on_payment_success(self, prepare_txn,
                                                execute_txn, add_new=False):
        prepare_txn.return_value = 'txid{}'.format(self.order.unique_reference)
        execute_txn.return_value = True
        address_id = 'span-withdraw-{}'.format(self.order.pk)

        try:
            self.wait.until(EC.element_to_be_clickable((
                By.ID, address_id
            ))).click()
        except TimeoutException:
            self.do_screenshot('TIMEOUT on Wait for address to be clickable')
        try:
            self.write_withdraw_address_on_popover(add_new=add_new)
        except Exception as e:
            self.do_screenshot('fail to add withdraw address: {}'.format(e),
                               refresh=True)
            if self.recursive_withdraw_calls < 1:
                self.add_withdraw_address_on_payment_success(add_new=add_new)
                self.recursive_withdraw_calls += 1
                return
            else:
                self.write_withdraw_address_on_popover(add_new=add_new)

        sleep(self.timeout / 30)
        self.do_screenshot('Withdraw Address added')

    def check_order_status(self, status):
        for _ in range(6):
            self.order.refresh_from_db()
            if self.order.status != status:
                sleep(self.timeout / 20)
            else:
                break
        self.assertEqual(
            self.order.status, status,
            'Bad Order status on {}'.format(self.payment_method))

    def check_order_status_indicator(self, indicator_name, checked=True,
                                     refresh=False):
        self.do_screenshot(
            'Before checking status \'{}\''.format(indicator_name),
            refresh=refresh
        )
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
                self.do_screenshot('wait for indicator', refresh=True)
                continue
            break
        self.assertNotEqual(
            len(indicator), 0,
            '{} order is not checked as {}'.format(
                self.payment_method, indicator_name
            )
        )

    def check_confirm_amounts(self, pair_name=None):
        try:
            self.wait.until(EC.element_to_be_clickable((
                By.CLASS_NAME, 'btc-amount-confirm')))
        except TimeoutException:
            # FIXME: sometimes unclickable is clicked (if you get there and
            # tests are still passing)
            self.do_screenshot(
                'TIMEOUT btc-amount-confirm is not clickable (tests should not'
                ' PASS cause you should not be abble to click unclickable '
                'element)'
            )
        amount_base = self.driver.find_element_by_class_name(
            'btc-amount-confirm').text
        amount_quote = self.driver.find_element_by_class_name(
            'cash-amount-confirm').text
        currency_base = self.driver.find_element_by_class_name(
            'currency_base').text
        # FIXME: legacy on frontend, class should be called
        # 'currency_quote'. Therefore XPATH is used here.
        currency_quote = self.driver.find_element_by_xpath(
            '//div[@id="menu3"]//span[@class="currency"]').text
        self.assertNotEqual(amount_base, '')
        self.assertNotEqual(amount_quote, '')
        if pair_name is not None:
            self.assertEqual(currency_base, pair_name[:3])
            self.assertEqual(currency_quote, pair_name[3:])
        res = {'currency_base': currency_base,
               'currency_quote': currency_quote,
               'amount_base': amount_base,
               'amount_quote': amount_quote}
        return res

    def click_go_to_order_list(self):
        try:
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@class="modal fade in"]//a')
            )).click()
        except TimeoutException:
            # FIXME: sometimes unclickable is clicked (if you get there and
            # tests are still passing)
            self.do_screenshot('TIMEOUT on click GO/Getcoins (tests should not'
                               ' PASS cause you should not be abble to click '
                               'unclickable element)')

    def mock_import_transaction(self, amount, currency_code, get_txs,
                                get_rtx):
        tx_id_api1 = 'tx_customer{}{}'.format(str(time()), randint(0, 999))
        tx_id_api2 = 'tx_customer{}{}'.format(str(time()), randint(0, 999))
        card_id = AddressReserve.objects.filter(
            user__username=self.username,
            currency__code=currency_code)[0].card_id
        get_txs_response = self.uphold_import_transactions_empty.format(
            tx_id_api1=tx_id_api1,
            tx_id_api2=tx_id_api2,
            amount1=amount,
            amount2='0.0',
            currency=currency_code,
            card_id=card_id,
        )

        get_txs.return_value = json.loads(get_txs_response)
        get_rtx.return_value = json.loads(self.completed)

    def do_screenshot(self, filename, refresh=False):
        now = time()
        diff = now - self.stamp
        self.stamp = now
        if refresh:
            self.driver.refresh()
            self.wait_page_load()
        path = os.path.join(
            self.screenpath, self.workflow, self.screenpath2)
        filename = '{}({}). {} ({:.2f}s)'.format(
            self.screenshot_no, self.screenshot_overall_no, filename, diff
        )
        self.mkdir(path)
        self.screenshot_no += 1
        self.screenshot_overall_no += 1
        print('{}/{}: {}'.format(self.workflow, self.screenpath2, filename))
        if self.issavescreen:
            self.driver.get_screenshot_as_file(
                os.path.join(path, filename + '.png'))
