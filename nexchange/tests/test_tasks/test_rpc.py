from unittest import TestCase, mock
from nexchange.api_clients.rpc import ScryptRpcApiClient
from core.models import Currency, Address


@mock.patch('nexchange.api_clients.rpc.ScryptRpcApiClient.lock')
@mock.patch('nexchange.api_clients.rpc.ScryptRpcApiClient.unlock')
@mock.patch('nexchange.api_clients.rpc.ScryptRpcApiClient.call_api')
@mock.patch('nexchange.api_clients.rpc.ScryptRpcApiClient.get_api')
@mock.patch('nexchange.api_clients.mappers.RpcMapper.get_pass')
class TestRpcEncryption(TestCase):
    def test_release_call_encrypt(self, get_pass, get_api, call_api, unlock, lock):
        get_pass.return_value = 'randomPass'
        get_api.return_value = mock.MagicMock()
        api = ScryptRpcApiClient()
        curr = Currency(code='BTC', wallet='rpc5')
        addr = Address()
        amount = 42
        api.release_coins(curr, addr, amount)
        self.assertEqual(call_api.call_count, 1)
        self.assertEqual(unlock.call_count, 1)
        get_api.assert_called_with('rpc5')

    def test_release_call_decrypt(self, get_pass, get_api, call_api, unlock, lock):
        get_pass.return_value = 'randomPass'
        get_api.return_value = mock.MagicMock()
        api = ScryptRpcApiClient()
        curr = Currency(code='BTC', wallet='rpc5')
        addr = Address()
        amount = 42
        api.release_coins(curr, addr, amount)
        self.assertEqual(call_api.call_count, 1)
        self.assertEqual(lock.call_count, 1)
        get_api.assert_called_with('rpc5')


@mock.patch('nexchange.api_clients.rpc.ScryptRpcApiClient.lock')
@mock.patch('nexchange.api_clients.rpc.ScryptRpcApiClient.unlock')
@mock.patch('nexchange.api_clients.rpc.ScryptRpcApiClient.call_api')
class TestRpcNonEncryption(TestCase):
    def test_balance_not_call_encrypt_decrypt(self, call_api, unlock, lock):
        api = ScryptRpcApiClient()
        curr = Currency(code='BTC', wallet='rpc5')
        api.get_balance(curr)
        self.assertEqual(call_api.call_count, 1)
        self.assertEqual(unlock.call_count, 0)
        self.assertEqual(lock.call_count, 0)

    def test_info_not_call_encrypt_decrypt(self, call_api, unlock, lock):
        api = ScryptRpcApiClient()
        curr = Currency(code='BTC', wallet='rpc5')
        api.get_info(curr)
        self.assertEqual(call_api.call_count, 1)
        self.assertEqual(unlock.call_count, 0)
        self.assertEqual(lock.call_count, 0)

