from core.tests.base import OrderBaseTestCase
from payments.api_clients.adv_cash import AdvCashAPIClient
from payments.tests.fixtures.adv_cash.transaction_history_empty import \
    response as history_response
from payments.tests.fixtures.adv_cash.transaction_empty import \
    response as transaction_response
from payments.tests.fixtures.adv_cash.send_money_empty import \
    response as send_money_response
from payments.models import PaymentPreference
from orders.models import Order
from django.conf import settings
from time import time
from unittest.mock import patch


class BaseAdvCashAPIClientTestCase(OrderBaseTestCase):

    def setUp(self):
        super(BaseAdvCashAPIClientTestCase, self).setUp()
        self.original_parameter_names = [
            'id', 'orderId', 'startTime', 'currency', 'transactionName',
            'amount', 'status', 'walletDestId', 'walletSrcId', 'senderEmail',
            'receiverEmail', 'fullCommission', 'direction', 'sci', 'comment'
        ]
        self.adv_cash_pref = PaymentPreference.objects.filter(
            user__is_staff=True,
            payment_method__name__icontains='advanced cash'
        ).first()
        self.order_data = {
            'amount_base': 0.1,
            'pair': self.BTCEUR,
            'user': self.user,
            'payment_preference': self.adv_cash_pref,
        }
        self.order = Order.objects.create(**self.order_data)
        self.sender_email = 'send@alot'
        self.sender_wallet = '123456789'
        self.payment_data = {
            'dest_wallet_id': settings.ADV_CASH_WALLET_EUR,
            'receiver_email': self.adv_cash_pref.identifier,
            'sender_email': self.sender_email,
            'src_wallet_id': self.sender_wallet,
            'amount': self.order.amount_quote,
            'currency': self.order.pair.quote.code,
            'comment': self.order.unique_reference,
            'unique_ref': self.order.unique_reference
        }

    def mock_advcash_transaction_response(self, tx_id=None, status='COMPLETED',
                                          dest_wallet_id='dest_wallet_id',
                                          src_wallet_id='src_wallet_id',
                                          sender_email='sender@email',
                                          receiver_email='receiver@email',
                                          amount='100.00', currency='EUR',
                                          fee='1.00', direction='INCOMING',
                                          unique_ref='12345', comment='12345'):
        if tx_id is None:
            tx_id = time()
        additional_fields = ''
        if unique_ref is not None:
            additional_fields += '<orderId>{}</orderId>'.format(unique_ref)
        transaction = transaction_response.format(
            id=tx_id, status=status, dest_wallet_id=dest_wallet_id,
            src_wallet_id=src_wallet_id, sender_email=sender_email,
            receiver_email=receiver_email, amount=amount, currency=currency,
            fee=fee, direction=direction, comment=comment,
            additional_fields=additional_fields)
        return transaction

    def mock_advcash_transaction_history_response(self, transactions=None,
                                                  return_bytes=True):
        if transactions is None:
            transactions = self.mock_advcash_transaction_response()
        history = history_response.format(transactions=transactions)
        if return_bytes:
            history = history.encode('utf-8')
        return history

    def mock_advcash_sendmoney_response(self, tx_id=None, return_bytes=True):
        if tx_id is None:
            tx_id = time()
        history = send_money_response.format(tx_id=tx_id)
        if return_bytes:
            history = history.encode('utf-8')
        return history

    def check_history_transactions_keys(self, transactions):
        for trans in transactions:
            self.check_transaction_keys(trans)

    def check_transaction_keys(self, transaction):
        transaction_keys = transaction.keys()
        for key in self.original_parameter_names:
            self.assertIn(key, transaction_keys)


class AdvCashAPIClientTestCase(BaseAdvCashAPIClientTestCase):

    def setUp(self):
        super(AdvCashAPIClientTestCase, self).setUp()
        self.api_client = AdvCashAPIClient()

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_get_history_transactions_of_1_txn(self, history_patch):
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response()
        res = self.api_client.get_transaction_history()
        self.assertEqual(1, len(res))
        self.check_history_transactions_keys(res)

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient.history')
    def test_get_history_transactions_of_0_txn(self, history_patch):
        history_patch.return_value = \
            self.mock_advcash_transaction_history_response(transactions='')
        res = self.api_client.get_transaction_history()
        self.assertEqual(0, len(res))

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient._send_money')
    def test_send_money(self, send_money_patch):
        tx_id = '123'
        send_money_patch.return_value = self.mock_advcash_sendmoney_response(
            tx_id=tx_id)
        res = self.api_client.send_money('1.00', 'EUR')
        self.assertEqual(tx_id, res['transaction_id'])
        self.assertEqual('OK', res['status'])

    @patch('payments.api_clients.adv_cash.AdvCashAPIClient._send_money')
    def test_send_money_error(self, send_money_patch):
        error_msg = 'Some Error'
        send_money_patch.side_effect = Exception(error_msg)
        res = self.api_client.send_money('1.00', 'EUR')
        self.assertIn(error_msg, res['message'])
        self.assertEqual('ERROR', res['status'])
