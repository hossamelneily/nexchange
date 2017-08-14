from unittest import TestCase

from payments.utils import (get_sha256_sign, get_payeer_desc,
                            credit_card_number_validator)


class UtilsTestCase(TestCase):

    def test_payeer_desc_generator(self):
        desc = get_payeer_desc('BUY 0.1BTC')
        expected = 'QlVZIDAuMUJUQw=='
        self.assertEqual(desc, expected)

    def test_payeer_sign_generator(self):
        m_orderid = '12345'
        m_amount = "%.2f" % 100.00
        m_curr = 'EUR'
        m_desc = get_payeer_desc('BUY 0.1BTC')
        m_shop = '287402376'
        m_key = '12345'
        sign = get_sha256_sign(ar_hash=(m_shop, m_orderid, m_amount, m_curr,
                                        m_desc, m_key))
        expected = ('0266597A232B49167A9551E015FECF0BC20D3D5185B31F81B02159E3'
                    '86E393BD')
        self.assertEqual(sign, expected)

    def test_credit_card_validator(self):
        # examples from
        # http://www.freeformatter.com/
        # credit-card-number-generator-validator.html
        valid_ccns = [
            '5393932585574906',
            '6011595607767392',
            '5414756004318701',
            '36776607099531',
            '6706940898715066',
            '6376755319882173',
            '4485240254652579',
            '379540054643851',
            '3539254363782712',
            '30548284759349',
            '5893961121444923',
            '4175007139180083'
        ]
        invalid_ccns = [
            '1234567887654321',
        ]
        for ccn in valid_ccns:
            res = credit_card_number_validator(ccn)
            self.assertTrue(res, ccn)
        for ccn in invalid_ccns:
            res = credit_card_number_validator(ccn)
            self.assertFalse(res, ccn)
