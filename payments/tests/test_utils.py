from unittest import TestCase

from payments.utils import get_payeer_sign, get_payeer_desc


class UtilsTestCase(TestCase):

    def test_payeer_desc_generator(self):
        desc = get_payeer_desc('BUY 0.1BTC')
        expected = 'QlVZIDAuMUJUQw=='
        self.assertEqual(desc, expected)

    def test_payeer_sign_generator(self):
        m_orderid = '12345'
        m_amount = 100.00
        m_curr = 'EUR'
        m_desc = get_payeer_desc('BUY 0.1BTC')
        m_shop = '287402376'
        m_key = '12345'
        sign = get_payeer_sign(m_orderid, m_amount, m_curr, m_desc,
                               m_shop=m_shop, m_key=m_key)
        expected = ('0266597A232B49167A9551E015FECF0BC20D3D5185B31F81B02159E3'
                    '86E393BD')
        self.assertEqual(sign, expected)
