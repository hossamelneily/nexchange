from core.models import Transaction, Currency
from orders.models import Order
from nexchange.tasks.base import BaseTask
from nexchange.utils import send_email
from nexchange.api_clients.factory import ApiClientFactory
from audit.models import SuspiciousTransactions, SuspiciousTransactionCategory
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import pytz
import numpy as np


class SuspiciousTransactionsChecker(BaseTask):

    def __init__(self, do_print=True, do_log=True):
        super(SuspiciousTransactionsChecker, self).__init__()
        self.do_print = do_print
        self.do_log = do_log

    def get_db_transactions(self, currency=None):
        txs = Transaction.objects.filter(
            currency__wallet=currency.wallet
        )
        return {tx.tx_id: {
            'pk': tx.pk,
            'tx_id': tx.tx_id,
            'amount': tx.amount,
            'currency': tx.currency.code,
            'decimals': tx.currency.decimals,
            'type': tx.type
        } for tx in txs}

    def _log(self, *args):
        if self.do_print:
            print(args)
        if self.do_log:
            self.logger.info(args)

    def process_ripple_txs(self, txs, accounts, **kwargs):
        currency = kwargs.get('currency')
        out_txs, in_txs, other_txs = [], [], []
        for tx in txs:
            try:
                raw_amount = tx.get('Amount', '0')
                # cause Amount sometimes can hold a dict
                assert isinstance(raw_amount, str)
                tx['amount'] = Decimal(str(raw_amount)) / Decimal(
                    '1E{}'.format(currency.decimals)
                )
                tx['tx_id'] = tx.get('hash', None)
                tx['time_stamp'] = tx.get('data', None)
                # tx['currency_code', currency.code)
                tx['from'] = tx.get('Account', None)
                tx['to'] = tx.get('Destination', None)
                if tx.get('TransactionType') == 'Payment':
                    if tx['Account'] not in accounts and \
                            tx['Destination'] in accounts:
                        in_txs.append(tx)
                    elif tx['Account'] in accounts and \
                            tx['Destination'] not in accounts:
                        tx['amount'] = - tx['amount']
                        out_txs.append(tx)
                elif tx['TransactionType'] != 'Payment':
                    other_txs.append(tx)
            except Exception as e:
                self._log(self._log('Got exception: {}, tx: {}'.format(e, tx)))
        return out_txs, in_txs, other_txs

    def process_cryptonight_txs(self, txs, accounts, **kwargs):
        pass

    def process_blake2_txs(self, txs, accounts, **kwargs):
        currency = kwargs.get('currency')
        out_txs, in_txs, other_txs = [], [], []
        for tx in txs:
            try:
                tx['tx_id'] = tx.get('hash')
                tx['time_stamp'] = None
                tx['to'] = tx.get('account')
                tx['from'] = None
                tx['amount'] = Decimal(str(tx.get('amount'))) / Decimal(
                    '1E{}'.format(currency.decimals)
                )
                if tx.get('type') == 'send' and \
                        tx.get('account') not in accounts:
                    tx['amount'] = - tx['amount']
                    out_txs.append(tx)
                elif tx.get('type') == 'receive' and \
                        tx.get('account') not in accounts:
                    in_txs.append(tx)
                elif tx.get('type') not in ['send', 'receive']:
                    other_txs.append(tx)
            except Exception as e:
                self._log(self._log('Got exception: {}, tx: {}'.format(e, tx)))
        return out_txs, in_txs, other_txs

    def process_omni_txs(self, txs, accounts, **kwargs):
        out_txs, in_txs, other_txs = [], [], []
        for tx in txs:
            try:
                tx['tx_id'] = tx.get('txid')
                tx['time_stamp'] = tx.get('blocktime')
                tx['to'] = tx.get('referenceaddress')
                tx['from'] = tx.get('sendingaddress')
                tx['amount'] = Decimal(str(tx['amount']))
                if tx.get('type') == 'Simple Send':
                    if tx['sendingaddress'] not in accounts and \
                            tx['referenceaddress'] in accounts:
                        in_txs.append(tx)
                    elif tx['sendingaddress'] in accounts and \
                            tx['referenceaddress'] not in accounts:
                        tx['amount'] = - tx['amount']
                        out_txs.append(tx)
                elif tx.get('type') != 'Simple Send':
                    other_txs.append(tx)
            except Exception as e:
                self._log(self._log('Got exception: {}, tx: {}'.format(e, tx)))
        return out_txs, in_txs, other_txs

    def process_scrypt_txs(self, txs, accounts, **kwargs):
        out_txs, in_txs, other_txs = [], [], []
        for tx in txs:
            try:
                tx['amount'] = Decimal(str(tx.get('amount')))
                tx['tx_id'] = tx.get('txid', None)
                tx['time_stamp'] = tx.get('time', None)
                if tx.get('category') == 'send' and \
                        tx.get('address') not in accounts:
                    tx['from'] = None  # should be value from accounts array
                    tx['to'] = tx.get('address', None)
                    out_txs.append(tx)
                elif tx.get('category') == 'receive' and \
                        tx.get('address') not in accounts:
                    tx['from'] = tx.get('address')
                    tx['to'] = None  # should be value from accounts array
                    in_txs.append(tx)
                elif tx.get('category') not in ['send', 'receive']:
                    other_txs.append(tx)
            except Exception as e:
                self._log(self._log('Got exception: {}, tx: {}'.format(e, tx)))
        return out_txs, in_txs, other_txs

    def process_ethash_txs(self, txs, accounts, **kwargs):
        client = kwargs.get('client')
        currency = kwargs.get('currency')
        out_txs, in_txs, other_txs = [], [], []
        for tx_data in txs:
            try:
                tx_id = tx_data.get('hash')
                tx_main_to = tx_data.get('to')
                _from = tx_data.get('from')
                tx_main_value = tx_data.get('value')
                if currency.is_token:
                    to = tx_data.get('to')
                    raw_amount = tx_main_value
                    currency_code = tx_data.get('tokenSymbol')
                else:
                    if tx_main_value == '0':
                        _currency = Currency.objects.filter(
                            contract_address__iexact=tx_main_to
                        ).last()
                        currency_code = _currency.code if _currency else ''
                        tx_input = tx_data.get('input')
                        to, raw_amount = \
                            client._get_transfer_data_from_eth_input(tx_input)
                        if to is None and raw_amount is None:
                            continue
                    else:
                        raw_amount = tx_main_value
                        to = tx_main_to
                        currency_code = 'ETH'
                if not currency_code:
                    continue
                try:
                    tx_currency = Currency.objects.get(code=currency_code)
                    decimals = tx_currency.decimals
                except ObjectDoesNotExist:
                    continue
                amount = Decimal(str(raw_amount)) / Decimal('1E{}'.format(
                    decimals))
                tx_data_decoded = {
                    'data': tx_data,
                    'currency_code': currency_code,
                    'to': to.lower(),
                    'from': _from.lower(),
                    'amount': Decimal(amount),
                    'tx_id': tx_id,
                    'time_stamp': tx_data.get('timeStamp')
                }
                accounts_lower = [acc.lower() for acc in accounts]
                if tx_data_decoded['from'] not in accounts_lower and \
                        tx_data_decoded['to'] in accounts_lower:
                    in_txs.append(tx_data_decoded)
                elif tx_data_decoded['from'] in accounts_lower and \
                        tx_data_decoded['to'] not in accounts_lower:
                    tx_data_decoded['amount'] = - tx_data_decoded['amount']
                    out_txs.append(tx_data_decoded)
            except Exception as e:
                self._log(self._log('Got exception: {}, tx: {}'
                                    .format(e, tx_data)))
        return out_txs, in_txs, other_txs

    def set_client_accounts_name(self, currency, client):
        if currency.wallet == 'rpc7':
            accounts = [acc.lower() for acc in
                        client.get_accounts(currency.wallet)]
            name = 'ethash'
        elif currency.code in ['DOGE', 'XVG', 'BCH', 'BTC', 'LTC', 'DASH',
                               'ZEC']:
            accounts = [acc for acc in
                        client.get_accounts(currency.wallet)]
            name = 'scrypt'
        elif currency.code == 'USDT':
            accounts = [acc for acc in
                        client.get_accounts(currency.wallet)]
            name = 'omni'
        elif currency.code == 'NANO':
            accounts = client.get_accounts(currency.wallet)
            name = 'blake2'
        elif currency.code == 'XMR':
            accounts = [acc.lower() for acc in
                        client.get_accounts(currency.wallet)]
            name = 'cryptonight'
        elif currency.code == 'XRP':
            accounts = [client.get_main_address(currency)]
            name = 'ripple'
        else:
            return None, None, None
        return accounts, name

    def get_wallet_transactions(
            self, currency=None,
            tx_count=settings.RPC_IMPORT_TRANSACTIONS_VALIDATION_COUNT
):
        factory = ApiClientFactory()
        client = factory.get_api_client(currency.wallet)
        accounts, name = self.set_client_accounts_name(currency, client)
        if all([client, accounts, name]):
            action = 'txlist' if not currency.is_token else 'tokentx'
            txs = client._list_txs(currency.wallet, tx_count=tx_count, action=action)
            process_txs_func = getattr(self, 'process_{}_txs'.format(name))
            out_txs, in_txs, other_txs = process_txs_func(
                txs, accounts, client=client, currency=currency
            )
        else:
            return None
        return {'out_txs': out_txs, 'in_txs': in_txs,
                'other_txs': other_txs}

    def is_right_ratio(self, ratio):
        return Decimal('1.00001') > ratio > Decimal('0.99999')

    def create_suspicious_tx(self, currency, categories_names, msg, tx):
        tx_id = tx.get('tx_id')
        tx_time_stamp = tx.get('time_stamp')
        tx_currency = tx.get('currency_code', currency.code)
        tx_amount = tx.get('amount')
        tx_from = tx.get('from')
        tx_to = tx.get('to')

        sus_tx, is_new = \
            SuspiciousTransactions.objects.get_or_create(tx_id=tx_id)
        categories_array = []
        for name in categories_names:
            cat, _ = \
                SuspiciousTransactionCategory.objects.get_or_create(name=name)
            if cat not in categories_array:
                categories_array.append(cat)
        if is_new:
            sus_tx.amount = tx_amount
            curr = Currency.objects.get(code=tx_currency)
            sus_tx.currency = curr
            sus_tx.address_from = tx_from
            sus_tx.address_to = tx_to
            sus_tx.auto_comment = msg
            sus_tx.categories.set(categories_array)
            if tx_time_stamp:
                sus_tx.time = datetime.fromtimestamp(
                    int(tx_time_stamp), tz=pytz.UTC
                )
            sus_tx.save()
            try:
                send_email(settings.SUPPORT_EMAIL,
                           'New suspicious transaction captured!', msg)
            except Exception as e:
                self._log('Email wasn\'t sent due to error: {}'.format(e))
        elif not is_new:
            used_categs = sus_tx.categories.all()
            unused_categs = np.setdiff1d(categories_array, used_categs)
            for cat in list(unused_categs):
                sus_tx.categories.add(cat)

        self._log(self.txs_count, tx_id, tx_amount, tx_currency,
                  tx_from, tx_to, msg)
        self.total_amount += tx_amount
        self.txs_count += 1

    def suspicious_transaction_check(self, currency, tx, db_txs):
        categories_names = []
        report = False
        msg = ''
        tx_id = tx.get('tx_id')
        tx_currency = tx.get('currency_code', currency.code)
        tx_amount = tx.get('amount')
        tx_to = tx.get('to')
        db_tx = db_txs.get(tx_id)
        if not db_tx:
            report = True
            categories_names.append('TRANSACTION IS NOT IN DATABASE')
        else:
            db_tx_amount = db_tx.get('amount')
            db_tx_currency = db_tx.get('currency')
            tx_db_ratio = abs(tx_amount) / Decimal(db_tx_amount)
            # 99.99 rule due to XVG wallet lack of last to
            # decimal places
            if all([abs(tx_amount) != db_tx_amount,
                    not self.is_right_ratio(tx_db_ratio)]):
                report = True
                categories_names.append('AMOUNTS MISMATCHING')
                msg += ' | Blockchain tx amount {} != {} tx DB amount'.\
                    format(tx_amount, db_tx_amount)
            if tx_currency != db_tx_currency:
                report = True
                categories_names.append('CURRENCIES MISMATCHING')
        if report:
            orders = Order.objects.filter(withdraw_address__address=tx_to)
            for order in orders:
                tx_order_ratio = abs(tx_amount) / Decimal(order.amount_base)
                if not self.is_right_ratio(tx_order_ratio):
                    currency.disabled = True
                    currency.save()
                    order_ref = order.unique_reference
                    msg += ' | Transaction amount is: {}, order {} withdraw ' \
                           'amount is: {}. Withdrawn to address: {}'.format(
                               tx_amount, order_ref, order.amount_base, tx_to
                           )
                    categories_names.append('WRONG SPEND')
            self.create_suspicious_tx(currency, categories_names, msg, tx)

    def run(self, currency):
        self._log('Check Out {}'.format(currency.code))
        self.txs_count = 0
        self.total_amount = Decimal('0')
        tx_import_amount = settings.RPC_IMPORT_TRANSACTIONS_VALIDATION_COUNT
        # another approach to get token txs and eth txs would be great
        if currency.wallet == 'rpc7':
            currs = [currency, Currency.objects.get(code='BNB')]
        else:
            currs = [currency]
        for curr in currs:
            blockchain_txs = self.get_wallet_transactions(
                currency=curr, tx_count=tx_import_amount
            )
            if not blockchain_txs:
                return
            out_txs = blockchain_txs['out_txs']
            in_txs = blockchain_txs['in_txs']
            other_txs = blockchain_txs['other_txs']
            db_txs = self.get_db_transactions(currency=currency)
            for tx in out_txs + other_txs + in_txs:
                try:
                    self.suspicious_transaction_check(curr, tx, db_txs)
                except Exception as e:
                    self._log('Got exception: {exc}, on tx: {tx}'
                              .format(exc=e, tx=tx))
        self._log('Total suspicious txs: {}, amount: {}, currency: {}'
                  .format(self.txs_count, self.total_amount, currency.code))
