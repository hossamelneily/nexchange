from core.tests.test_ui.base import BaseTestUI
import requests_mock
from accounts.models import SmsToken
from core.tests.utils import data_provider
from selenium.webdriver.common.by import By
import re


class TestUILogin(BaseTestUI):

    def setUp(self):
        super(TestUILogin, self).setUp()
        self.workflow = 'LOGIN'

    @data_provider(lambda: ((False,), (True,)), )
    def test_otm_login_phone(self, push_resend):
        self.base_otp_login(self.phone, push_resend)

    @data_provider(lambda: ((False,), (True,)), )
    def test_otm_login_email(self, push_resend):
        self.base_otp_login(self.email, push_resend)

    @requests_mock.mock()
    def base_otp_login(self, username, push_resend, mock):
        mock.post(
            'https://www.google.com/recaptcha/api/siteverify',
            text='{\n "success": true\n}'
        )
        self.screenpath2 = 'OTP'
        if push_resend:
            self.screenpath2 += '_resend'
        self.screenshot_no = 1
        self.get_repeat_on_timeout(self.url)
        self.do_screenshot('main')
        self.click_element_by_name('Login', by=By.XPATH)
        self.assertIn('accounts/login', self.driver.current_url)
        self.fill_element_by_id('id_username', username)
        self.click_element_by_name('send-otp')
        self.wait_until_clickable_element_by_name('login-otp',
                                                  screenshot=True)
        if push_resend:
            self.click_element_by_name('resend-otp', screenshot=True)
        token = SmsToken.objects.get(user__username=username).sms_token
        self.fill_element_by_id('id_password', token)
        self.click_element_by_name('login-otp', screenshot=True)
        self.wait_until_clickable_element_by_name('trigger-buy',
                                                  screenshot=True)
        self.assertIn('buy_bitcoin', self.driver.current_url)
        profile_link = self.driver.find_elements_by_xpath(
            self.xpath_query_contains_text.format(username)
        )
        self.assertEqual(len(profile_link), 1)
        self.logout()


class TestUIProfile(BaseTestUI):

    def setUp(self):
        super(TestUIProfile, self).setUp()
        self.username = self.email
        self.otp_login(self.username)

    def test_profile_referrals(self):
        self.do_screenshot('main')

        self.click_element_by_name('{}'.format(self.username), by=By.XPATH)
        self.click_element_by_name('referrals_button', by=By.ID,
                                   screenshot=True)
        before_codes = len(self.driver.find_elements_by_class_name('line-hr'))
        self.click_element_by_name('new-referral-code', by=By.ID,
                                   screenshot=True)
        self.wait_until_clickable_element_by_name('code_new', by=By.NAME,
                                                  screenshot=True)
        xpath_query = '//form[@id="new-referral-code-form"]//input[@type="{}"]'
        self.click_element_by_name(
            'submit', by=By.XPATH,
            xpath_query=xpath_query)
        self.wait_page_load(delay=0.2)
        self.assertIn('tab=referrals', self.driver.current_url)
        after_codes = len(self.driver.find_elements_by_class_name('line-hr'))
        self.assertEqual(before_codes + 1, after_codes)
        self.click_element_by_name('new-referral-code', by=By.ID,
                                   screenshot=True)
        not_random_name = 'not_random_name'
        self.fill_element_by_id('code_new', not_random_name)
        self.click_element_by_name(
            'submit', by=By.XPATH,
            xpath_query=xpath_query)
        self.wait_page_load(delay=0.2)
        src = self.driver.page_source
        text_found = re.search(r'{}'.format(not_random_name), src)
        self.assertNotEqual(text_found, None)
