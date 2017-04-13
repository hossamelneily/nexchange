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
from payments.models import UserCards
from verification.models import Verification
from django.conf import settings
from django.contrib.auth.models import User

from accounts.models import SmsToken
from unittest.mock import patch
import requests_mock
from time import time
import json


class BaseTestUI(StaticLiveServerTestCase, TransactionImportBaseTestCase,
                 TickerBaseTestCase):

    def setUp(self):
        super(BaseTestUI, self).setUp()
        self.workflow = 'generic'
        self.phone = '+37068644145'
        self.email = 'sarunas@onin.ws'
        self.name = 'Sir Testalot'
        self.account = 'LT121000011101001000'
        self.card_number = '1234567887654321'
        self.swift_iban = '987654321'
        self.bic = 'DABAIE2D'
        self.withdraw_address = '1GR9k1GCxJnL3B5yryW8Kvz7JGf31n8AGi'
        self.issavescreen = True
        self.url = self.live_server_url
        self.screenpath = os.path.join(
            os.path.dirname(__file__), 'Screenshots', str(time()))
        self.screenpath2 = 'unsorted'
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
        sleep(self.timeout / 10)

    def get_currency_pair_main_screen(self, pair_name, lang='en'):
        url = '{}/{}/orders/buy_bitcoin/{}/'.format(self.url, lang,
                                                    pair_name)
        self.get_repeat_on_timeout(url)

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

    def logout(self):
        self.driver.delete_all_cookies()
        self.logged_in = False

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
        if not self.selenium_user.profile.is_verified:
            Verification(user=self.selenium_user, id_status=Verification.OK,
                         util_status=Verification.OK).save()
        sleep(self.timeout / 20)
        self.do_screenshot('After Login')
        self.logged_in = True

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

    @patch('nexchange.utils.api.execute_txn')
    @patch('nexchange.utils.api.prepare_txn')
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
        sleep(self.timeout / 5)
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
        self.do_screenshot(
            'Before checking status \'{}\''.format(indicator_name)
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

    def mock_import_transaction(self, amount, currency_code, reserve_txs,
                                import_txs):
        tx_id_api = 'tx_customer' + str(time())
        reserve_txs.return_value = json.loads(self.completed)
        card_id = UserCards.objects.filter(
            user__profile__phone=self.phone,
            currency=currency_code)[0].card_id
        get_txs_response = self.uphold_import_transactions_empty.format(
            tx_id_api1=tx_id_api,
            tx_id_api2='nonsense',
            amount1=amount,
            amount2='0.0',
            currency=currency_code,
            card_id=card_id,
        )
        import_txs.return_value = json.loads(get_txs_response)

    def do_screenshot(self, filename, refresh=False):
        now = time()
        diff = now - self.stamp
        self.stamp = now
        if refresh:
            self.driver.refresh()
            sleep(self.timeout / 6)
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
