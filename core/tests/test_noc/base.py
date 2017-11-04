from time import sleep
from random import randint
from decimal import Decimal

from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from unittest import TestCase
import requests
from nexchange.utils import get_nexchange_logger
from nexchange.utils import get_transaction_blockchain
from orders.models import Order
import time


class BaseTestLiveOrders(TestCase):

    def setUp(self):
        super(BaseTestLiveOrders, self).setUp()
        self.logger = get_nexchange_logger(
            'Live Test Logger', with_email=False, with_console=True
        )
        self.private_key = 'private_key'  # noqa
        self.driver = webdriver.Chrome()
        self.driver.set_window_size(1400, 1000)

    def order_endpoint(self, ref=None):
        return 'https://api.nexchange.io/en/api/v1/orders/{}/'.format(ref)

    def random_amount(self, multiplier=0.0001, min_val=21, max_val=52):
        res = Decimal(
            str(randint(min_val, max_val))) * Decimal(str(multiplier))
        return res

    def create_order(self, pair_name='BTCETH',
                     withdraw_address='3P7HftbJek8J3vNm8WrhuuVhDj1U1EjRaR',
                     amount_base=0.008):
        deposit_address = deposit_amount = deposit_currency_code = None
        payload = {
            "amount_base": str(amount_base),
            "is_default_rule": False,
            "pair": {
                "name": pair_name
            },
            "withdraw_address": {
                "address": withdraw_address
            }
        }

        create_order_url = 'https://nexchange.io/en/api/v1/orders/'

        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(create_order_url, data=json.dumps(payload),
                                 headers=headers)
        if response.status_code == 201:
            json_resp = response.json()
            deposit_address = json_resp['deposit_address']['address']
            deposit_currency_code = json_resp['deposit_address'][
                'currency_code']
            deposit_amount = json_resp['amount_quote']
        return {'deposit_amount': deposit_amount,
                'deposit_currency_code': deposit_currency_code,
                'deposit_address': deposit_address,
                'order': json_resp}

    def send_funds_eth_wallet(self, amount, address):
        url = 'https://www.myetherwallet.com/#send-transaction'
        xpath_checkbox = '//input[@value="pasteprivkey"]'
        xpath_private_key = '//textarea'
        xpath_unlock = '//a[@translate="ADD_Label_6_short"]'
        xpath_address = '//input[@ng-model="addressDrtv.ensAddressField"]'
        xpath_amount = '//input[@ng-model="tx.value"]'
        xpath_generate_tx = '//a[@ng-click="generateTx()"]'
        xpath_send_tx = '//a[@translate="SEND_trans"]'
        xpath_approve_tx = '//button[@ng-click="sendTx()"]'
        self.driver.get(url)
        sleep(0.5)
        self.driver.find_element(By.XPATH, xpath_checkbox).click()
        sleep(0.5)
        priv_elem = self.driver.find_element(By.XPATH, xpath_private_key)
        priv_elem.send_keys(self.private_key)
        sleep(0.5)
        self.driver.find_element(By.XPATH, xpath_unlock).click()
        sleep(0.5)
        self.driver.find_element(By.XPATH, xpath_address).send_keys(address)
        sleep(0.5)
        self.driver.find_element(By.XPATH, xpath_amount).send_keys(amount)
        sleep(2)
        self.driver.find_element(By.XPATH, xpath_generate_tx).click()
        sleep(2)
        self.driver.find_element(By.XPATH, xpath_send_tx).click()
        sleep(3)
        self.driver.find_element(By.XPATH, xpath_approve_tx).click()
        sleep(2)

    def get_transaction_id_from_eth_wallet_success_msg(self):
        sleep(3)
        xpath_tx = "//div[@class='alert-message ng-binding']//p/strong"
        tx_id_strong = self.driver.find_element(By.XPATH, xpath_tx)
        outgoing_tx_id = tx_id_strong.text
        print()
        print('Outgoing Transaction id: {}'.format(outgoing_tx_id))
        sleep(2)
        return outgoing_tx_id

    def get_order_in_status_names(self, in_statuses):
        statuses_db = []
        statuses_name = []
        for status in in_statuses:
            res = [st for st in Order.STATUS_TYPES if st[0] == status][0]
            statuses_db.append(res[0])
            statuses_name.append(res[1])
        return statuses_db, statuses_name

    def get_order_paid_should_be_status(self, tx_id):
        self.confirmations = get_transaction_blockchain('ETH', tx_id)[1]
        if self.confirmations == 0:
            return self.get_order_in_status_names([Order.INITIAL])
        try:
            currencies = requests.get(
                'https://api.nexchange.io/en/api/v1/currency/').json()
            eth = [curr for curr in currencies if curr['code'] == 'ETH'][0]
            min_confirmations = eth['min_confirmations']
        except Exception:
            min_confirmations = 12
        if self.confirmations < min_confirmations:
            return self.get_order_in_status_names([Order.PAID_UNCONFIRMED])
        else:
            return self.get_order_in_status_names(Order.IN_PAID)

    def check_tx_till_paid_status(self, order_ref, tx_id):
        start = time.time()
        checked = False
        while not checked:
            now = time.time()
            time_from_tx = time.strftime('%H:%M:%S', time.gmtime(now - start))
            checked = self.check_paid_status(
                order_ref, tx_id, time_from_tx=time_from_tx)
            if not checked:
                time.sleep(30)

    def check_paid_status(self, order_ref, tx_id, time_from_tx=None):
        status_msg = 'ok'
        paid_status_should_be = self.get_order_paid_should_be_status(tx_id)

        order_url = self.order_endpoint(ref=order_ref)
        try:
            order_info = requests.get(order_url).json()
        except Exception:
            order_info = {}
        order_status = order_info.get('status_name', [[None, None]])[0]
        order_status_db = order_status[0]
        order_status_name = order_status[1]
        if order_status_db not in paid_status_should_be[0]:
            status_msg = 'not ok'
        msg = 'time from tx send: {after} | {status_msg} | ' \
              'order: {order_ref} | tx_deposit: {tx_id} ' \
              'confs: {confirmations} | is: {order_status} | must be in : ' \
              '{should_status_in}'.format(
                  after=time_from_tx,
                  status_msg=status_msg,
                  order_ref=order_ref,
                  tx_id=tx_id,
                  confirmations=self.confirmations,
                  order_status=order_status_name,
                  should_status_in=paid_status_should_be[1]
              )
        self.logger.info(msg)
        if order_status_db in Order.IN_PAID:
            return True
        return False

    def tearDown(self):
        super(BaseTestLiveOrders, self).tearDown()
        self.driver.close()
