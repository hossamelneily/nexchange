from django.conf import settings
import requests
from core.models import Currency, Location
from orders.models import Order
from payments.models import Payment, PaymentMethod, PaymentPreference,\
    FailedRequest
from nexchange.utils import get_nexchange_logger
from decimal import Decimal
from copy import deepcopy
from payments.utils import credit_card_number_validator
from datetime import date
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
        self.order = None

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
            msg = _('CVV({}) length is not 3'.format(cvv))
            self.logger.warning(msg)
            return {'status': 0, 'msg': msg}
        try:
            int(cvv)
        except ValueError:
            msg = _('CVV({}) contains not only digits'.format(cvv))
            self.logger.warning(msg)
            return {'status': 0, 'msg': msg}
        return {'status': 1, 'msg': 'OK'}

    def _validate_mastercard_ccn(self, ccn):
        if ccn[:2] not in ['51', '52', '53', '54', '55']:
            msg = _(
                'cnn({}) starts with wrong numbers for mastercard'.format(ccn)
            )
            self.logger.warning(msg)
            return {'status': 0, 'msg': msg}
        if len(ccn) < 16 or len(ccn) > 19:
            msg = _(
                'Mastercard cnn({}) must be between 16-19 digits long'.format(
                    ccn
                )
            )
            self.logger.warning(msg)
            return {'status': 0, 'msg': msg}
        if not credit_card_number_validator(ccn):
            msg = _(
                ' {} is invalid Mastercard number.'.format(ccn)
            )
            self.logger.warning(msg)
            return {'status': 0, 'msg': msg}
        return {'status': 1, 'msg': 'OK'}

    def _validate_ccexp(self, ccexp):
        if len(ccexp) != 4:
            msg = _('Invalid ccexp({}) length'.format(ccexp))
            self.logger.warning(msg)
            return {'status': 0, 'msg': msg}
        yy = int('20{}'.format(ccexp[2:]))
        if ccexp[0] == 0:
            mm = int(ccexp[1:2])
        else:
            mm = int(ccexp[:2])
        now = date.today()
        day_exp = date(yy, mm, 1)
        if now >= day_exp:
            msg = _(
                'Credit card expired (ccexp - {})'.format(ccexp)
            )
            self.logger.warning(msg)
            return {'status': 0, 'msg': msg}
        return {'status': 1, 'msg': 'OK'}

    def _validate_credit_card_crediantials(self, **kwargs):
        cvv_valid = self._validate_cvv(kwargs['cvv'])
        if cvv_valid['status'] == 0:
            return {'status': 0, 'msg': cvv_valid['msg']}
        ccn_valid = self._validate_mastercard_ccn(kwargs['ccn'])
        if ccn_valid['status'] == 0:
            return {'status': 0, 'msg': ccn_valid['msg']}
        ccexp_valid = self._validate_ccexp(kwargs['ccexp'])
        if ccexp_valid['status'] == 0:
            return {'status': 0, 'msg': ccexp_valid['msg']}
        return {'status': 1, 'msg': 'OK'}

    def check_for_response_failures(self, formatted_response, content, url,
                                    **kwargs):
        failed = False
        if formatted_response['status'] == '0'\
                or formatted_response['transaction_id'] == '0':
            failed = True
        for value in formatted_response.values():
            if value is None:
                failed = True
        if failed:
            failure = FailedRequest(url=url, response=content,
                                    order=self.order, payload=kwargs)
            failure.save()

    def create_transaction(self, **kwargs):
        valid = self._validate_credit_card_crediantials(**kwargs)
        if valid['status'] == 0:
            failure = FailedRequest(validation_error=valid['msg'],
                                    order=self.order, payload=kwargs)
            failure.save()
            return {
                'status': 0, 'msg': valid['msg']
            }
        url = self._create_tx_url(**kwargs)
        response = requests.get(url, verify=False)
        content = response.content.decode('utf-8')
        res = {
            'status': self._read_content_table_parameter(content, 'STATUS'),
            'transaction_id': self._read_content_table_parameter(
                content, 'TRANSACTION_ID'),
            'response_code': self._read_content_table_parameter(
                content, 'RESPONSE_CODE'),
        }
        self.check_for_response_failures(res, content, url, **kwargs)
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
                cvv=kwargs['cvv'],
                ccexp=kwargs['ccexp'],
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
        self.order = Order.objects.get(unique_reference=kwargs['orderid'])
        if self.validate_order(self.order, **kwargs):
            try:
                res = self.create_transaction(**kwargs)
            except KeyError as e:
                error_msg = _('Bad Credit Card credentials')
                return {'status': 0, 'msg': error_msg}
            if res['status'] == '1':
                self.order.status = Order.PAID_UNCONFIRMED
                self.order.save()
                if res['transaction_id'] == '0' or res['transaction_id'] is \
                        None:
                    error_msg = _('Order payment status is unclear, please '
                                  'contact administrator!')
                    return {'status': 0, 'msg': error_msg}
                if not self.check_unique_transaction_id(res['transaction_id']):
                    return {'status': 0, 'msg': error_msg}
                self.order.status = Order.PAID
                self.order.save()
                pref = self.create_payment_preference(self.order, **kwargs)
                currency = Currency.objects.get(code=kwargs['currency'])
                payment = Payment(
                    is_success=res['status'],
                    payment_system_id=res['transaction_id'],
                    reference=self.order.unique_reference,
                    amount_cash=kwargs['amount'],
                    payment_preference=pref,
                    order=self.order,
                    user=self.order.user if self.order else None,
                    currency=currency
                )
                payment.save()
                return {'status': 1, 'msg': success_msg}
            elif 'msg' in res:
                return res
            else:
                self.logger.error(
                    'Bad Payment status. response:{},order:{}'.format(
                        res, self.order
                    )
                )
                return {'status': 0, 'msg': error_msg}
        else:
            if self.order.status == Order.PAID:
                error_msg = _("This order is already paid")
            return {'status': 0, 'msg': error_msg}
