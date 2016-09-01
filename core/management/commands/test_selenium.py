from selenium import webdriver
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import os
import sys
from django.core.management.base import BaseCommand
from core.models import SmsToken


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.issavescreen = False
        self.screenpath = os.path.join(
            os.path.dirname(__file__), 'Screenshots')
        if not os.path.exists(self.screenpath):
            os.makedirs(self.screenpath)
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64)' \
                     ' AppleWebKit/537.36 (KHTML, like Gecko)' \
                     ' Chrome/37.0.2062.120 Safari/537.36'
        self.dcap = dict(DesiredCapabilities.PHANTOMJS)
        self.dcap["phantomjs.page.settings.userAgent"] = user_agent
        self.timeout = 5

    def handle(self, *args, **options):
        banks = ['alfa-bank', 'Sberbank', 'Qiwi wallet']
        print('Test buy')
        for b in banks:
            try:
                self.checkbuy(b)
            except Exception as e:
                print(b + " " + str(e))
                sys.exit(1)

    def checkbuy(self, paymethod):
        print(paymethod)
        driver = webdriver.PhantomJS(
            service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any'],
            desired_capabilities=self.dcap)
        driver.set_window_size(1400, 1000)
        driver.set_page_load_timeout(10)

        wait = WebDriverWait(driver, self.timeout)

        driver.get('http://localhost:8000/')
        self.doscreenshot(driver, 'main_')
        btbuy = wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'trigger-buy')))
        btbuy.click()
        sleep(1)
        self.doscreenshot(driver, 'after buy click')
        payments = driver.\
            find_elements_by_class_name('payment-method-icon')
        paybank = None
        for p in payments:
            try:
                alt = p.get_attribute('alt').lower()
            except:
                continue
            if alt == paymethod.lower() and p.is_displayed():
                paybank = p
                break

        sleep(2)
        paybank.click()
        sleep(2)
        self.doscreenshot(driver, 'after bank click')
        phone = driver.find_elements_by_class_name('phone')

        test_phone = '1111'
        phone[1].send_keys(test_phone)

        self.doscreenshot(driver, 'after input phone number')
        btnes = driver.find_elements_by_class_name('create-acc')
        # enter send sms
        for btsendsms in btnes:
            if btsendsms.get_attribute('class')\
                    .find('btn-primary') > -1:
                btsendsms.click()
                break
        sleep(2)
        # input sms code
        last_sms = SmsToken.objects.filter().latest('id').sms_token
        ver_code = wait.until(EC.element_to_be_clickable(
            (By.ID, 'verification_code')))

        ver_code.send_keys(last_sms)

        self.doscreenshot(driver, 'after input code number')

        driver.execute_script('window.submit_phone()')
        sleep(1)
        self.doscreenshot(driver, 'after verifycate phone')
        # press buy
        bt_buys = driver.find_elements_by_class_name('buy-go')
        for b in bt_buys:
            if b.get_attribute('class') \
                    .find('place-order') > -1:
                b.click()
                break
        wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'unique_ref')))
        self.doscreenshot(driver, 'End')
        print('Ok')
        driver.close()

    def doscreenshot(self, driver, filename):
        if self.issavescreen:
            driver.get_screenshot_as_file(
                os.path.join(self.screenpath, filename + '.png'))
