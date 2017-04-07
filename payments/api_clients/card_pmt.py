from django.conf import settings
import requests
from core.models import Currency, Location
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference
from nexchange.utils import get_nexchange_logger
from decimal import Decimal
from copy import deepcopy
from payments.utils import credit_card_number_validator
from datetime import date
from core.tests.utils import read_fixture
from time import time
from urllib.parse import quote_plus
from django.utils.translation import ugettext_lazy as _


class CardPmtAPIClient:

    LOGIN_PARAMETERS = 'username={username}&password={password}'
    TEST_MODE = 'test_mode={test_mode_int}'
    REQUIRED_TRANSACTION_PARAMETERS = \
        'type=sale&totamt={amount}&currency={currency}&ccn={ccn}' \
        '&ccexp={ccexp}&cvv={cvv}&orderid={orderid}&orderdesc={desc}' \
        '&bfn={firstname}&bln={lastname}&bcountry={country_code}' \
        '&bstate={state_or_province}&baddress1={address1}&bcity={city}' \
        '&bzip={zip}&bphone={phone}&bemail={email}&sasaba=1' \
        '&customer_ip={ip}&subaffiliate_id=1&rebill=0&affiliate_id=1' \
        '&affiliate_name=random' \
        '&website=https://nexchange.co.uk&reply_format=html'

    def __init__(self, url=None, username=None, password=None, test_mode=None):
        self.logger = get_nexchange_logger(
            self.__class__.__name__,
            True,
            True
        )
        if url is None:
            self.url = settings.CARDPMT_API_URL
        else:
            self.url = url
        if username is None:
            username = settings.CARDPMT_API_ID
        else:
            username = username
        if password is None:
            password = settings.CARDPMT_API_PASS
        else:
            password = password
        if test_mode is None:
            test_mode = settings.CARDPMT_TEST_MODE
        else:
            test_mode = test_mode
        if test_mode:
            test_mode_int = 1
        else:
            test_mode_int = 0
        login_params = self.LOGIN_PARAMETERS.format(username=username,
                                                    password=password)
        test_params = self.TEST_MODE.format(test_mode_int=test_mode_int)
        self.initial_url = '{}?{}&{}'.format(self.url, login_params,
                                             test_params)
        self.name = 'Mastercard-Internal'
        self.payment_method = PaymentMethod.objects.get(
            name__icontains=self.name
        )

    def _create_tx_url(self, **kwargs):
        encoded_dict = {}
        for key in kwargs:
            encoded_dict.update({key: quote_plus(kwargs[key])})
        tx_parameters = self.REQUIRED_TRANSACTION_PARAMETERS.format(
            **encoded_dict
        )
        url = self.initial_url + '&' + tx_parameters
        if 'address2' in encoded_dict:
            if encoded_dict['address2'] != '':
                url = url + '&' + encoded_dict['address2']
        return url

    def _read_content_table_parameter(self, content, parameter):
        try:
            value = content.split(
                '<tr><td>{}</td><td>'.format(parameter)
            )[1].split('</td></tr>')[0]
        except IndexError:
            value = None
        return value

    def _validate_cvv(self, cvv):
        if len(cvv) != 3:
            self.logger.warning('cvv({}) length is not 3'.format(cvv))
            return False
        try:
            int(cvv)
        except ValueError:
            self.logger.warning('cvv({}) contains not only digits'.format(cvv))
            return False
        return True

    def _validate_mastercard_ccn(self, ccn):
        if ccn[:2] not in ['51', '52', '53', '54', '55']:
            self.logger.warning(
                'cnn({}) starts with wrong numbers for mastercard'.format(ccn)
            )
            return False
        if len(ccn) < 16 or len(ccn) > 19:
            self.logger.warning(
                ' mastercard cnn({}) must be between 16-19 digits long'.format(
                    ccn
                )
            )
            return False
        if not credit_card_number_validator(ccn):
            self.logger.warning(
                ' ccn({}) bad checksum'.format(ccn)
            )
            return False
        return True

    def _validate_ccexp(self, ccexp):
        if len(ccexp) != 4:
            self.logger.warning('Invalid ccexp({}) length'.format(ccexp))
            return False
        yy = int('20{}'.format(ccexp[2:]))
        if ccexp[0] == 0:
            mm = int(ccexp[1:2])
        else:
            mm = int(ccexp[:2])
        now = date.today()
        day_exp = date(yy, mm, 1)
        if now >= day_exp:
            self.logger.warning(
                'Credit card expired (ccexp - {})'.format(ccexp)
            )
            return False
        return True

    def _validate_credit_card_crediantials(self, **kwargs):
        if not self._validate_cvv(kwargs['cvv']):
            self.logger.warning('Invalid cvv')
            return False
        if not self._validate_mastercard_ccn(kwargs['ccn']):
            self.logger.warning('Invalid cvv')
            return False
        if not self._validate_ccexp(kwargs['ccexp']):
            self.logger.warning('Invalid ccexp')
            return False
        return True

    def create_transaction(self, **kwargs):
        if not self._validate_credit_card_crediantials(**kwargs):
            return {
                'status': 0, 'msg': _('Bad Credit Card credentials')
            }
        url = self._create_tx_url(**kwargs)
        if settings.CREDIT_CARD_IS_TEST:
            response_empty = read_fixture(
                'payments/tests/fixtures/card_pmt/'
                'transaction_response_empty.html'
            )
            content = response_empty.format(
                auth_code='100',
                status='1',
                transaction_id=str(time())
            )
        else:
            response = requests.get(url, verify=False)
            content = response.content.decode('utf-8')
        res = {
            'status': self._read_content_table_parameter(content, 'STATUS'),
            'transaction_id': self._read_content_table_parameter(
                content, 'TRANSACTION_ID'),
            'response_code': self._read_content_table_parameter(
                content, 'RESPONSE_CODE'),
        }
        return res

    def validate_order(self, order, **kwargs):
        if order.amount_quote != Decimal(kwargs['amount']):
            return False
        if order.pair.quote.code != kwargs['currency']:
            return False
        if order.status != Order.INITIAL:
            return False
        return True

    def create_location(self, user, **kwargs):
        location_filter = {
            'firstname': kwargs['firstname'],
            'lastname': kwargs['lastname'],
            'zip': kwargs['zip'],
            'country': kwargs['country_code'],
            'state': kwargs['state_or_province'],
            'city': kwargs['city'],
            'address1': kwargs['address1'],
            'user': user
        }
        if 'address2' in kwargs:
            location_filter['address2'] = kwargs['address2']
        location = Location.objects.get_or_create(**location_filter)[0]
        return location

    def create_payment_preference(self, order=None, **kwargs):
        identifier = kwargs['ccn']
        secondary_identifier = '{} {}'.format(
            kwargs['firstname'], kwargs['lastname']
        )
        user = order.user if order else None
        filters = {
            'payment_method': self.payment_method,
            'user': user
        }
        pref1_filters = deepcopy(filters)
        pref1_filters.update({'identifier': identifier})
        pref1 = PaymentPreference.objects.filter(
            **pref1_filters
        )
        pref2_filters = deepcopy(filters)
        pref1_filters.update(
            {'secondary_identifier': secondary_identifier}
        )

        pref2 = PaymentPreference.objects.filter(
            **pref2_filters
        )
        new_pref = not pref1 and not pref2
        if pref1 and pref2 and pref1[0] != pref2[0]:
            self.logger.error('found duplicate payment preferences {} {}'
                              .format(pref1, pref2))
        if new_pref:
            # creating a pref without a user, after payment
            # will be matched with an order we will assign it
            # to the user who made the order
            pref = PaymentPreference.objects.create(
                identifier=identifier,
                secondary_identifier=secondary_identifier,
                payment_method=self.payment_method,
                user=user
            )
            if not order:
                flag, created = pref.flag()
                if created:
                    self.logger.warn('perf: {} without owner and order'
                                     .format(pref))

            self.logger.info(
                'payment preference created {} {} {}'.format(
                    pref, identifier, secondary_identifier))
        else:
            pref = pref1[0] if pref1 else pref2[0]

        location = self.create_location(user, **kwargs)
        if pref.location != location:
            pref.location = location

        pref.save()

        return pref

    def check_unique_transaction_id(self, transaction_id):
        if transaction_id == 0:
            return False
        payments = Payment.objects.filter(payment_system_id=transaction_id)
        if len(payments) > 0:
            self.logger.error(
                'Payments({}) with transaction_id({}) already exists'.format(
                    payments, transaction_id
                )
            )
            return False
        return True

    def pay_for_the_order(self, **kwargs):
        error_msg = _('Something went wrong. Order is not paid.')
        success_msg = _('Order is paid successfully!')
        order = Order.objects.get(unique_reference=kwargs['orderid'])
        if self.validate_order(order, **kwargs):
            try:
                res = self.create_transaction(**kwargs)
            except KeyError:
                error_msg = _('Bad Credit Card credentials')
                return {'status': 0, 'msg': error_msg}
            if res['status'] == '1':
                order.status = Order.PAID_UNCONFIRMED
                order.save()
                if res['transaction_id'] == '0' or res['transaction_id'] is \
                        None:
                    error_msg = _('Order payment status is unclear, please '
                                  'contact administrator!')
                    return {'status': 0, 'msg': error_msg}
                if not self.check_unique_transaction_id(res['transaction_id']):
                    return {'status': 0, 'msg': error_msg}
                order.status = Order.PAID
                order.save()
                pref = self.create_payment_preference(order, **kwargs)
                currency = Currency.objects.get(code=kwargs['currency'])
                payment = Payment(
                    is_success=res['status'],
                    payment_system_id=res['transaction_id'],
                    reference=order.unique_reference,
                    amount_cash=kwargs['amount'],
                    payment_preference=pref,
                    order=order,
                    user=order.user if order else None,
                    currency=currency
                )
                payment.save()
                return {'status': 1, 'msg': success_msg}
            elif 'msg' in res:
                return res
            else:
                self.logger.error(
                    'Bad Payment status. response:{},order:{}'.format(res,
                                                                      order)
                )
                return {'status': 0, 'msg': error_msg}
        else:
            if order.status == Order.PAID:
                error_msg = _("This order is already paid")
            return {'status': 0, 'msg': error_msg}
