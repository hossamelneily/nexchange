from nexchange.api_clients.decorators import track_tx_mapper, log_errors, encrypted_endpoint
from nexchange.rpc.base import BaseRpcClient
from core.models import Address
from django.conf import settings
import os
from http.client import RemoteDisconnected
from decimal import Decimal


class ScryptRpcApiClient(BaseRpcClient):
    LOCK_WALLET = 'walletlock'
    UNLOCK_WALLET = 'walletpassphrase'

    def __init__(self):
        super(ScryptRpcApiClient, self).__init__()
        self.related_nodes = ['rpc2', 'rpc3', 'rpc4', 'rpc5', 'rpc6']
        self.related_coins = ['DOGE', 'XVG', 'BCH', 'BTC', 'LTC']

    def lock(self, api, **kwargs):
        encrypt_fn = getattr(api, self.LOCK_WALLET)
        return encrypt_fn()

    def unlock(self, api, pass_phrase, **kwargs):
        decrypt_fn = getattr(api, self.UNLOCK_WALLET)
        return decrypt_fn(*[pass_phrase, settings.WALLET_TIMEOUT])

    def get_fn(self, api, endpoint):
        return getattr(api, endpoint)

    def create_address(self, currency):
        address = self.call_api(currency.wallet, 'getnewaddress')
        return {
            'currency': currency,
            'address': address
        }

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'wallet': node})

        try:
            _address = self.get_address({'address': tx['address']})
        except Address.DoesNotExist:
            _address = None
            self.logger.warning(
                'Could not find Address {}'.format(Address)
            )

        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'amount': tx['amount'],
            # TODO: check if right type is sent by the wallet
            'time': tx['time'],
            'tx_id': tx['txid'],
            'tx_id_api': None,
        }

    def filter_tx(self, tx):
        return tx['category'] == 'receive'

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'gettransaction', *[tx_id])
        return tx

    def check_tx(self, tx, currency):
        # this assumes that currency and node are one to one except uphold
        tx = self._get_tx(tx.tx_id, currency.wallet)
        confirmations = tx['confirmations']
        confirmed = all([confirmations >= currency.min_confirmations,
                         confirmations > 0])
        return confirmed, confirmations

    def _get_txs(self, node):
        txs = self.call_api(node, 'listtransactions',
                            *["", settings.RPC_IMPORT_TRANSACTIONS_COUNT])
        return txs

    def get_accounts(self, node):
        return self.call_api(node, 'getaddressesbyaccount', *[""])

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(ScryptRpcApiClient, self).get_txs(node, txs)

    @encrypted_endpoint
    def release_coins(self, currency, address, amount, **kwargs):
        _address = getattr(address, 'address', address)
        tx_id = self.call_api(currency.wallet, 'sendtoaddress',
                              *[_address, amount])
        success = True
        return tx_id, success

    def get_unspent_address_balance(self, node, address, min_confs=1):
        _address = getattr(address, 'address', address)
        res = self.call_api(node, 'listunspent')
        return Decimal(
            sum([x['amount'] for x in res if x['address'] == _address and x['confirmations'] > min_confs])  # noqa
        )

    def get_balance(self, currency):
        balance = self.call_api(currency.wallet, 'getbalance')
        return balance

    def get_info(self, currency):
        method = 'getwalletinfo' if currency.code in ['BTC'] else 'getinfo'
        info = self.call_api(currency.wallet, method)
        return info

    def health_check(self, currency):
        try:
            info = self.get_info(currency)
        except RemoteDisconnected:
            # First request always fails after timeout.
            # If this one fails - smth is wrong with rpc connection in general
            info = self.get_info(currency)
        assert isinstance(info, dict)
        return super(ScryptRpcApiClient, self).health_check(currency)

    def backup_wallet(self, currency):
        path = os.path.join(settings.WALLET_BACKUP_PATH,
                            currency.code)
        self.call_api(currency.wallet, 'backupwallet', *[path])
