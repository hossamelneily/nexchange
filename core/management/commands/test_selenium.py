from selenium import webdriver
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.desired_capabilities
#  import DesiredCapabilities
import os
from django.core.management.base import BaseCommand
# from core.models import SmsToken


class TestBuyOrder(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(TestBuyOrder, self).__init__(*args, **kwargs)
        self.screenpath = os.path.join(
            os.path.dirname(__file__), 'Screenshots')
        if not os.path.exists(self.screenpath):
            os.makedirs(self.screenpath)
        # dcap = dict(DesiredCapabilities.PHANTOMJS)
        # self.driver = webdriver.PhantomJS(
        # service_args=['--ignore-ssl-errors=true',
        #  '--ssl-protocol=any'],desired_capabilities=dcap)
        self.driver = webdriver.Firefox()
        self.driver.set_window_size(1400, 1000)
        self.driver.set_page_load_timeout(10)
        self.timeout = 5
        self.wait = WebDriverWait(self.driver, self.timeout)

    def handle(self, *args, **options):
        self.driver.get('http://localhost:8000/')
        self.driver.get_screenshot_as_file(
            os.path.join(self.screenpath, 'main.png'))
        btbuy = self.wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'trigger-buy')))
        btbuy.click()
        self.driver.get_screenshot_as_file(
            os.path.join(self.screenpath, 'after buy click.png'))
        payments = self.driver.\
            find_elements_by_class_name('payment-method-icon')
        paybank = None
        for p in payments:
            try:
                alt = p.get_attribute('alt')[:4].lower()
            except:
                continue
            if alt == 'alfa':
                paybank = p
                break
        if paybank is None:
            return False
        print(paybank.get_attribute('alt'))
        self.driver.get_screenshot_as_file(
            os.path.join(self.screenpath, 'after bank click.png'))
        paybank.click()
        self.waitJS()
        # wait = WebDriverWait(self.driver, 10)
        # self.wait.until(
        # EC.invisibility_of_element_located((By.NAME, 'phone')))
        sleep(3)
        phone = self.driver.find_elements_by_class_name('phone')
        print(phone[1].get_attribute('class'))
        phone[1].send_keys('1111111111')
        # phone.click()
        self.driver.get_screenshot_as_file(
            os.path.join(self.screenpath, 'after input number.png'))
        btnes = self.driver.find_elements_by_class_name('create-acc')
        for btsendsms in btnes:
            if btsendsms.get_attribute('class')\
                    .find('btn-primary') > -1:
                btsendsms.click()
                break
        # input sms code

    def waitJS(self):
        for i in range(0, 10):
            done = \
                self.driver.execute_script(
                    "return document.readyState") == "complete"
            if done:
                break
            else:
                sleep(1)
