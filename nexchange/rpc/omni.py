from nexchange.api_clients.decorators import track_tx_mapper, log_errors, encrypted_endpoint
from nexchange.rpc.scrypt import ScryptRpcApiClient
from core.models import Address, Currency
from django.conf import settings
import os


class OmniRpcApiClient(ScryptRpcApiClient):
    def __init__(self):
        super(OmniRpcApiClient, self).__init__()
        self.related_nodes = ['rpc10']
        self.related_coins = ['USDT']

    def is_correct_token(self, tx, currency):
        if tx['propertyid'] == currency.property_id:
            return True
        else:
            return False

    def is_simple_send_type(self, tx):
        if tx['type_int'] == 0:
            return True
        else:
            return False

    def is_tx_vald(self, tx):
        return tx['valid']

    def check_tx(self, tx, currency):
        tx = self._get_tx(tx.tx_id, currency.wallet)
        confirmations = tx['confirmations']
        confirmed = all([confirmations >= currency.min_confirmations,
                         confirmations > 0,
                         self.is_correct_token(tx, currency),
                         self.is_simple_send_type(tx),
                         self.is_tx_vald(tx)])
        return confirmed, confirmations

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'code': tx['currency_code']})
        to = tx['to']
        try:
            _address = self.get_address({'address': to.lower()})
        except Address.DoesNotExist:
            _address = None
            self.logger.warning(
                'Could not find Address {}'.format(Address)
            )
        return {
            # required
            'currency': _currency,
            'address_to': _address,
            'amount': tx['value'],
            'tx_id': tx['tx_id'],
            'tx_id_api': None,
        }

    def _get_tx(self, tx_id, node):
        tx = self.call_api(node, 'omni_gettransaction', *[tx_id])
        return tx

    def get_accounts(self, node):
        return self.call_api(node, 'getaddressesbyaccount', *[""])

    def get_main_address(self, currency):
        node = currency.wallet
        address = os.getenv('{}_PUBLIC_KEY_C1'.format(node.upper()))
        all_accounts = self.get_accounts(node)
        assert address in all_accounts, \
            'Main address must be in get_accounts resp {}'.format(currency)
        return address

    def _form_transaction(self, currency, address, amount, **kwargs):
        if isinstance(address, Address):
            address_to = address.address
        else:
            address_to = address
        main_address = self.get_main_address(currency)
        address_from = kwargs.get('address_from', main_address)

        tx = {
            'fromaddress': address_from,
            'toaddress': address_to,
            'propertyid': currency.property_id,
            'amount': amount
        }

        return tx

    @encrypted_endpoint
    def release_coins(self, currency, address, amount, **kwargs):
        tx = self._form_transaction(currency, address, amount, **kwargs)
        tx_id = self.call_api(currency.wallet, 'omni_send',
                              *[tx])
        success = True
        return tx_id, success

    def get_balance(self, currency, account=None):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        if account is None:
            account = self.get_main_address(currency)
        balance = self.call_api(currency.wallet, 'omni_getbalance',
                                *[account, currency.property_id])
        return balance

    def get_info(self, currency):
        info = self.call_api(currency.wallet, 'omni_getinfo')
        return info

    def _get_txs(self, node):
        txs = self._get_txs_from_blocks(node)
        return txs

    def filter_tx(self, tx):
        return True

    def _get_current_block(self, node):
        res = self.call_api(node, 'omni_getinfo')
        return res.get('block')

    def _get_txs_from_blocks(self, node, start_block_number=None,
                             end_block_number=None, accounts=None):
        res = []
        currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        accounts = accounts if accounts \
            else self.call_api(node,
                               'getaddressesbyaccount',
                               '')
        if end_block_number is None:
            end_block_number = self._get_current_block(node)

        if start_block_number is None:
            start_block_number = \
                end_block_number - settings.RPC_IMPORT_BLOCK_COUNT

        for i in range(start_block_number, end_block_number + 1):
            txs_hashes = self.call_api(node, 'omni_listblocktransactions', i)
            if not txs_hashes:
                continue
            for tx_hash in txs_hashes:
                tx = self._get_tx(tx_hash, node)
                tx_id = tx.get('txid')
                main_to = tx.get('referenceaddress')
                _from = tx.get('sendingaddress')
                main_value = tx.get('amount')

                value = main_value
                to = main_to
                currency_code = currency.code
                if not currency_code or not isinstance(to, str):
                    continue
                if all([to.lower() not in [acc.lower() for acc in accounts]]):
                    continue
                res.append({
                    'data': tx,
                    'currency_code': currency_code,
                    'to': to,
                    'from': _from,
                    'value': value,
                    'tx_id': tx_id
                })
        return res

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(ScryptRpcApiClient, self).get_txs(node, txs)
