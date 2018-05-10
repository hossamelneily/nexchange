from core.models import Transaction, Currency
from orders.models import Order
from nexchange.tasks.base import BaseTask
from nexchange.api_clients.rpc import EthashRpcApiClient, ScryptRpcApiClient
from audit.models import SuspiciousTransactions
import requests
import os
from decimal import Decimal
from datetime import datetime


class SuspiciousTransactionsChecker(BaseTask):

    def __init__(self, do_print=True, do_log=True):
        super(SuspiciousTransactionsChecker, self).__init__()
        self.do_print = do_print
        self.do_log = do_log

    def get_db_transactions(self, currency='ETH'):
        currency = Currency.objects.get(code=currency)
        txs = Transaction.objects.filter(
            currency__wallet=currency.wallet, tx_id_api__isnull=True
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

    def get_wallet_transactions(self, currency='ETH'):
        internal_addresses = {
            'XVG': {'DK978nKHAAgzG1wWRwLWdk6AHNiy7RCqn9': 'bittrex'},
            'BTC': {
                '189gddoj1UNbTbXSNm656V8dseF3z7acFu': 'bittrex',
                '1F41mU67RW65dP8r7SeDBMXt7QU9v8ftK6': 'own'
            },
        }
        cold_addresses = {
            'BTC': {
                '1F41mU67RW65dP8r7SeDBMXt7QU9v8ftK6': 'own'
            }
        }
        main_addresses = {
            'BTC': {
                '13mkbEWnPafyzEBsJq82ceY4Zom9quUAbU': 'own'
            }
        }
        out_txs, in_txs, other_txs = [], [], []
        if currency == 'ETH':
            client = EthashRpcApiClient()
            accounts = [acc.lower() for acc in client.get_accounts('rpc7')]
            main_account = os.getenv('RPC7_PUBLIC_KEY_C1')
            url = \
                'http://api.etherscan.io/api?module=account&action=txlist' \
                '&address={}&startblock=0&endblock=99999999&sort=asc' \
                '&apikey=YourApiKeyToken'.format(main_account)
            res = requests.get(url)
            txs = res.json()['result']
            out_txs = []
            in_txs = []
            other_txs = []
            for tx_data in txs:
                tx_id = tx_data.get('hash')
                main_to = tx_data.get('to')
                _from = tx_data.get('from')
                main_value = tx_data.get('value')
                if main_value == '0':
                    _currency = Currency.objects.filter(
                        contract_address__iexact=main_to).last()
                    currency_code = _currency.code if _currency else ''
                    decimals = _currency.decimals if _currency else 18
                    input = tx_data.get('input')
                    decoded_input = client.decode_transaction_input(input)
                    try:
                        if decoded_input[0] in client.ERC20_TRANSFER_FINCTIONS:
                            to = client._strip_address_padding(
                                decoded_input[1][0]
                            )
                            value = int(decoded_input[1][1], 16)
                            amount = Decimal(value) / Decimal(10**decimals)
                    except IndexError:
                        continue
                else:
                    amount = Decimal(main_value) / Decimal(10**18)
                    to = main_to
                    currency_code = 'ETH'
                if not currency_code:
                    continue
                tx_data_decoded = {
                    'data': tx_data,
                    'currency_code': currency_code,
                    'to': to,
                    'from': _from,
                    'amount': amount,
                    'tx_id': tx_id,
                    'time_stamp': tx_data.get('timeStamp')
                }
                if tx_data_decoded['from'].lower() == main_account.lower():
                    tx_data_decoded['internal'] = \
                        True if tx_data_decoded['to'] in accounts else False
                    tx_data_decoded['amount'] = - tx_data_decoded['amount']
                    out_txs.append(tx_data_decoded)
                elif tx_data_decoded['to'].lower() == main_account.lower():
                    tx_data_decoded['internal'] = \
                        True if tx_data_decoded['from'] in accounts else False
                    in_txs.append(tx_data_decoded)
                else:
                    tx_data_decoded['internal'] = None
                    other_txs.append(tx_data_decoded)
            return {'out_txs': out_txs, 'in_txs': in_txs,
                    'other_txs': other_txs}
        if currency in ['XVG', 'BTC', 'BCH', 'DOGE', 'LTC', 'ZEC', 'USDT']:
            _currency = Currency.objects.get(code=currency)
            client = ScryptRpcApiClient()
            txs = client.call_api(_currency.wallet,
                                  'listtransactions',
                                  *["", 10000])
            out_txs = [tx for tx in txs if tx.get('category') == 'send']
            for tx in out_txs:
                tx['internal'] = True if tx['address'] in internal_addresses.get(currency, []) else False  # noqa
            for tx in out_txs:
                tx['to_cold_storage'] = True if tx['address'] in cold_addresses.get(currency, []) else False  # noqa
            in_txs = [tx for tx in txs if tx.get('category') == 'receive']
            for tx in in_txs:
                tx['to_main_address'] = True if tx['address'] in main_addresses.get(currency, []) else False  # noqa

            other_txs = [
                tx for tx in txs if tx.get('category') not in ['send',
                                                               'receive']
            ]
        return {'out_txs': out_txs, 'in_txs': in_txs,
                'other_txs': other_txs}

    def run(self, currency_code):
        blockchain_txs = self.get_wallet_transactions(currency=currency_code)
        out_txs = blockchain_txs['out_txs']
        in_txs = blockchain_txs['in_txs']  # noqa
        # Skip ETH due to its resend_to_main_transactions
        to_main = [] if currency_code == 'ETH' else [
            tx for tx in in_txs if tx.get('to_main_address')
        ]
        other_txs = blockchain_txs['other_txs']
        db_txs = self.get_db_transactions(currency=currency_code)
        self._log('Check Out {}'.format(currency_code))
        i = 1
        total_amount = Decimal('0')
        for tx in out_txs + other_txs + to_main:
            tx_id = tx.get('tx_id', tx.get('txid'))
            time_stamp = tx.get('time_stamp', tx.get('time'))
            amount = tx['amount']
            report = False
            msg = ''
            internal = tx.get('internal')
            to_cold_storage = tx.get('to_cold_storage')
            to_main = tx.get('to_main_address')
            tx_currency = tx.get('currency_code', currency_code)
            _from = tx.get('from')
            _to = tx.get('to', tx.get('address'))
            tx_db = db_txs.get(tx_id)
            if not tx_db:
                if to_cold_storage or to_main or not internal:
                    report = True
                    msg += '*tx_id not found in DB'
            else:
                # 99.99 rule due to XVG wallet lack of last to decimal places
                if all([abs(amount) != tx_db['amount'],
                       not Decimal('1.00001') > (abs(amount) / tx_db['amount']) > Decimal('0.99999')]):  # noqa

                    report = True
                    msg += \
                        '*Blockchain value {} does not correspond amount of ' \
                        'the tx in DB {}'.format(tx['amount'], tx_db['amount'])
                if tx_currency != tx_db['currency']:
                    report = True
                    msg += \
                        '*Blockchain currency {} does not correspond to DB ' \
                        'currency {}'.format(tx['currency_code'],
                                             tx_db['currency'])
            if report:
                orders = Order.objects.filter(withdraw_address__address=_to)
                for order in orders:
                    msg += '* withdraw_address of order {}'.format(
                        order.unique_reference
                    )
                    if Decimal('1.00001') > (abs(amount) / order.amount_base) > Decimal('0.99999'):  # noqa
                        msg += ' DOUBLE SPEND'
                self._log(i, tx_id, amount, tx_currency, _from, _to, msg)
                sus_tx, created = SuspiciousTransactions.objects.get_or_create(
                    tx_id=tx_id
                )
                if created:
                    sus_tx.amount = amount
                    curr = Currency.objects.get(code=tx_currency)
                    sus_tx.currency = curr
                    sus_tx.address_from = _from
                    sus_tx.address_to = _to
                    sus_tx.auto_comment = msg
                    if time_stamp:
                        sus_tx.time = datetime.fromtimestamp(int(time_stamp))
                    if to_cold_storage:
                        sus_tx.human_comment = 'To Cold Storage'
                        sus_tx.approved = True
                    sus_tx.save()

                i += 1
                total_amount += amount
        self._log('Total suspicious amount {} {}'.format(total_amount,
                  currency_code))
