from __future__ import absolute_import
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q

from core.models import Transaction, Currency
from orders.models import Order, LimitOrder
from nexchange.utils import get_nexchange_logger
from risk_management.task_summary import order_cover_invoke
from nexchange.utils import convert_camel_to_snake_case
from copy import deepcopy


class BaseTransactionImporter:
    def __init__(self):
        self.transactions = None
        self.logger = get_nexchange_logger(
            self.__class__.__name__
        )

    def get_orders(self, tx_data, status=Order.INITIAL):
        buy_exchange_query = {
            'exchange': True,
            'order_type': Order.BUY,
            'pair__quote': tx_data['currency'],
            'status': status,
            'deposit_address': tx_data['address_to']
        }
        if tx_data.get('destination_tag'):
            buy_exchange_query['destination_tag'] = \
                tx_data.get('destination_tag')

        if tx_data.get('payment_id'):
            buy_exchange_query['payment_id'] = tx_data.get('payment_id')

        orders = Order.objects.filter(**buy_exchange_query)
        if not orders:
            sell_limit_query = deepcopy(buy_exchange_query)
            sell_limit_query.pop('pair__quote')
            sell_limit_query.update({
                'pair__base': tx_data['currency'],
                'order_type': Order.SELL,
            })
            orders = LimitOrder.objects.filter(
                Q(**buy_exchange_query) | Q(**sell_limit_query)
            )

        return orders

    def get_or_create_tx(self, tx):
        existing_transaction = None
        try:
            if tx['tx_id'] and tx['tx_id_api']:
                query = (
                    Q(tx_id=tx['tx_id']) |
                    Q(tx_id_api=tx['tx_id_api'])
                )
            elif not tx['tx_id'] and tx['tx_id_api']:
                query = Q(tx_id_api=tx['tx_id_api'])
            elif tx['tx_id'] and not tx['tx_id_api']:
                query = Q(tx_id=tx['tx_id'])
            else:
                raise ValueError(
                    'Transaction data does not contain any information about '
                    'transaction({}) id(tx_id) or api_id(tx_api_id)'.format(tx)
                )
            existing_transaction = Transaction.objects.get(
                query
            )
        except MultipleObjectsReturned as e:
            self.logger.error('more than one same transactions exists in DB {}'
                              .format(tx))
            raise e
        except Transaction.DoesNotExist:
            self.logger.info('{} transaction not found in DB, creating new...'
                             .format(tx))
        except ValueError as e:
            self.logger.info(e)
            raise e

        if existing_transaction:
            self.logger.info('Transaction with ID {} already exists'.format(
                tx['tx_id'])
            )
            self.api.revert_tx_mapper()
        else:
            self.create_tx(tx)

    def update_unconfirmed_order(self, orders, tx_data):
        pass

    def create_tx(self, tx_data):
        tx = None
        orders = self.get_orders(tx_data)
        if len(orders) == 1:
            order = orders[0]

            tx_data.update({
                convert_camel_to_snake_case(order.__class__.__name__): order,
                'type': Transaction.DEPOSIT
            })

            register_res = order.register_deposit(tx_data)

            if register_res.get('status') == 'OK':
                tx = register_res.get('tx')
                self.logger.info('New transaction created {}'
                                 .format(tx.__dict__))
                self.logger.info('Order {} is marked as PAID_UNCONFIRMED'
                                 .format(order.__dict__))
                order_cover_invoke.apply_async([order.pk])
            else:
                self.logger.error(
                    'Failed transaction register. response: {} order: {}. '
                    'tx_data: {}.'.format(
                        register_res, order.unique_reference, tx_data))
        elif len(orders) == 0:
            self.logger.info(
                'Transaction is not created: no orders for transaction '
                '{} found'.format(tx_data))
            unconfirmed_orders = self.get_orders(tx_data,
                                                 status=Order.PAID_UNCONFIRMED)
            if len(unconfirmed_orders) == 1:
                self.update_unconfirmed_order(unconfirmed_orders[0],
                                              tx_data)
        elif len(orders) > 1:
            self.logger.error(
                'Transaction is not created: more then 1 order {} found'
                ' for transaction {}'.format(orders, tx_data))

    def import_income_transactions(self):
        # Note: this will only work if node and currency
        # are one to one
        for node in self.api.related_nodes:
            currencies = Currency.objects.filter(wallet=node)
            skip = True
            for currency in currencies:
                if currency.is_quote_of_enabled_pair_for_test:
                    skip = False
            if skip:
                continue
            try:
                total_txs, txs = self.api.get_txs(node)
                for tx in txs:
                    if tx['address_to'] is not None:
                        self.get_or_create_tx(tx)
                    else:
                        self.logger.info(
                            'Transaction has no address_to: {}'.format(tx))
            except TypeError:
                self.logger.warning('node {} is not working'.format(node))
