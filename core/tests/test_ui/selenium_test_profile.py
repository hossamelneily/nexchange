from core.tests.test_ui.base import BaseTestUI
import requests_mock
from accounts.models import SmsToken
from core.tests.utils import data_provider
from selenium.webdriver.common.by import By


class TestUIProfile(BaseTestUI):

    @data_provider(lambda: ((False,), (True,)), )
    @requests_mock.mock()
    def test_otp_login(self, push_resend, mock):
        mock.post(
            'https://www.google.com/recaptcha/api/siteverify',
            text='{\n "success": true\n}'
        )
        self.workflow = 'PROFILE'
        self.screenpath2 = 'OTP'
        if push_resend:
            self.screenpath2 += '_resend'
        self.screenshot_no = 1
        self.get_repeat_on_timeout(self.url)
        self.do_screenshot('main')
        self.click_element_by_name('Login', by=By.XPATH)
        self.assertIn('accounts/login', self.driver.current_url)
        self.fill_element_by_id('id_username', self.phone)
        self.click_element_by_name('send-otp')
        self.wait_until_clickable_element_by_name('login-otp',
                                                  screenshot=True)
        if push_resend:
            self.click_element_by_name('resend-otp', screenshot=True)
        token = SmsToken.objects.get(user__profile__phone=self.phone).sms_token
        self.fill_element_by_id('id_password', token)
        self.click_element_by_name('login-otp', screenshot=True)
        self.wait_until_clickable_element_by_name('trigger-buy',
                                                  screenshot=True)
        self.assertIn('buy_bitcoin', self.driver.current_url)
        profile_link = self.driver.find_elements_by_xpath(
            self.xpath_query_contains_text.format(self.phone)
        )
        self.assertEqual(len(profile_link), 1)
        self.logout()
