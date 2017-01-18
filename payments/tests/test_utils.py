from unittest import TestCase

from payments.utils import get_payeer_sign


class UtilsTestCase(TestCase):

    def test_payeer_sign_generator(self):
        m_orderid = '12345'
        m_amount = 100.0
        m_curr = 'EUR'
        order_type = 'BUY'
        amount_btc = 0.1
        sign = get_payeer_sign(m_orderid, m_amount, m_curr, order_type,
                               amount_btc)
        self.assertIsNotNone(sign)
