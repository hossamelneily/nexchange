from nexchange.api_clients.decorators import \
    track_tx_mapper, log_errors, encrypted_endpoint
from nexchange.rpc.scrypt import ScryptRpcApiClient
from core.models import Address, Currency, AddressReserve
from decimal import Decimal
import os
from django.core.exceptions import ValidationError
from django.conf import settings


class OmniRpcApiClient(ScryptRpcApiClient):
    def __init__(self):
        super(OmniRpcApiClient, self).__init__()
        self.related_nodes = ['rpc10']
        self.related_coins = ['USDT']

    def is_correct_token(self, tx, currency):
        return True if tx['propertyid'] == currency.property_id else False

    def is_simple_send_type(self, tx):
        return True if tx['type_int'] == 0 else False

    def is_tx_valid(self, tx):
        return tx['valid']

    def check_tx(self, tx, currency):
        tx = self._get_tx(tx.tx_id, currency.wallet)
        confirmations = tx['confirmations']
        confirmed = all([confirmations >= currency.min_confirmations,
                         confirmations > 0,
                         self.is_correct_token(tx, currency),
                         self.is_simple_send_type(tx),
                         self.is_tx_valid(tx)])
        return confirmed, confirmations

    def parse_tx(self, tx, node=None):
        _currency = self.get_currency({'code': tx['currency_code']})
        to = tx['to']
        try:
            _address = self.get_address({'address': to})
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
                              *[tx['fromaddress'], tx['toaddress'],
                                tx['propertyid'], str(tx['amount'])])
        success = True
        return tx_id, success

    def add_btc_to_card(self, card_pk):
        card = AddressReserve.objects.get(pk=card_pk)
        address = card.address
        currency = Currency.objects.get(code='BTC')
        amount = card.currency.tx_price.amount_btc
        return super(OmniRpcApiClient, self).release_coins(
            currency, address, amount
        )

    def check_card_balance(self, card_pk, **kwargs):
        card = AddressReserve.objects.get(pk=card_pk)
        res = self.resend_funds_to_main_card(card.address, card.currency.code)
        return res

    def resend_funds_to_main_card(self, address, currency):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        btc_avail = self.get_unspent_address_balance(currency.wallet, address)
        if btc_avail != 0 and btc_avail >= currency.tx_price.amount_btc:
            main_address = self.get_main_address(currency)
            amount = self.get_balance(currency, account=address).get(
                'available', Decimal('0')
            )

            if amount <= 0:
                return {'success': False, 'retry': True}
            tx_id, success = self.release_coins(currency, main_address,
                                                amount, address_from=address)
            retry = not success
            return {'success': success, 'retry': retry, 'tx_id': tx_id}
        else:
            return {'success': False, 'retry': True}

    def get_balance(self, currency, account=None):
        if not isinstance(currency, Currency):
            currency = Currency.objects.get(code=currency)
        if account is None:
            account = self.get_main_address(currency)
        res = self.call_api(currency.wallet, 'omni_getbalance',
                            *[account, currency.property_id])
        balance = Decimal(res.get('balance', '0'))
        pending = Decimal(res.get('reserved', '0'))
        available = balance - pending
        return {'balance': balance, 'pending': pending, 'available': available}

    def get_info(self, currency):
        info = self.call_api(currency.wallet, 'omni_getinfo')
        return info

    def _list_txs(self, node, **kwargs):
        tx_count = kwargs.get('tx_count',
                              settings.RPC_IMPORT_TRANSACTIONS_COUNT)
        txs = self.call_api(node, 'omni_listtransactions',
                            *["", tx_count])
        return txs

    def _get_txs(self, node):
        txs = self.call_api(node, 'omni_listpendingtransactions')
        currency = Currency.objects.get(
            code=self.related_coins[self.related_nodes.index(node)]
        )
        in_txs = [tx for tx in txs
                  if tx.get('referenceaddress') in self.get_accounts(node)]
        res = []
        for in_tx in in_txs:
            res.append({
                'data': in_tx,
                'currency_code': currency.code,
                'to': in_tx['referenceaddress'],
                'from': in_tx['sendingaddress'],
                'value': in_tx['amount'],
                'tx_id': in_tx['txid']
            })
        return res

    def filter_tx(self, tx):
        return True

    @log_errors
    @track_tx_mapper
    def get_txs(self, node=None, txs=None):
        txs = self._get_txs(node)
        return super(ScryptRpcApiClient, self).get_txs(node, txs)

    def assert_tx_unique(self, currency, address, amount, **kwargs):
        txs = self._list_txs(
            currency.wallet,
            tx_count=settings.RPC_IMPORT_TRANSACTIONS_VALIDATION_COUNT
        )
        _address = getattr(address, 'address', address)
        _amount = Decimal(str(amount))
        same_transactions = [
            tx for tx in txs if
            Decimal(tx['amount']) == _amount and
            tx['referenceaddress'] == _address
        ]
        if same_transactions:
            raise ValidationError(
                'Transaction of {amount} {currency} to {address} already '
                'exist. Tx: {tx_list}'.format(
                    amount=amount, address=_address, currency=currency,
                    tx_list=same_transactions
                )
            )
