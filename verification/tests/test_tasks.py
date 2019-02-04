from unittest.mock import patch
from core.tests.base import OrderBaseTestCase, VerificationBaseTestCase
from core.tests.utils import data_provider
from verification.models import Verification, VerificationDocument, \
    DocumentType, VerificationCategory, CategoryRule
from payments.models import PaymentPreference, PaymentMethod
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from datetime import timedelta, datetime
from verification.task_summary import check_kyc_pending_documents_periodic
from decimal import Decimal


class VerificationStatusesTestCase(OrderBaseTestCase,
                                   VerificationBaseTestCase):

    def setUp(self):
        super(VerificationStatusesTestCase, self).setUp()

        self.api_client = APIClient()
        self.order = self._create_order_api()
        self.pref = PaymentPreference.objects.create(
            payment_method=PaymentMethod.objects.get(name='Safe Charge'),
            provider_system_id=self.generate_txn_id(),
            secondary_identifier=self.generate_txn_id()
        )
        payment_data = {
            'order': self.order, 'currency': self.order.pair.quote,
            'amount_cash': self.order.amount_quote,
            'payment_preference': self.pref,
            'type': 'D'
        }
        self.order.register_deposit(payment_data, crypto=False)
        self.order.user.email = "much@email.such"
        self.order.user.save()

    def _create_verification(self, order_ref):
        self.api_client.post(
            '/en/api/v1/kyc/',
            {'order_reference': order_ref},
            format='json')
        return Verification.objects.get(note=order_ref)

    @data_provider(
        lambda: (
            (0, 1, ['UTIL'], ['PENDING']),
            (0, 2, ['UTIL', 'UTIL'], ['PENDING', 'REJECTED']),
            (1, 1, ['UTIL'], ['REJECTED']),
            (1, 2, ['UTIL', 'UTIL'], ['REJECTED', 'REJECTED']),
            (1, 2, ['UTIL', 'ID'], ['REJECTED', 'REJECTED']),
            (1, 1, ['SELFIE'], ['REJECTED']),
            (1, 1, ['WHITELIST_SELFIE'], ['REJECTED']),
            (0, 3, ['ID', 'ID', 'ID'], ['REJECTED', 'PENDING', 'REJECTED']),
        )
    )
    @patch('payments.models.send_email')
    def test_notify_user_on_rejected_kyc_document(self,
                                                  expected_send_email_count,
                                                  document_count, doc_types,
                                                  doc_statuses,
                                                  mock_send_email):
        verification = self._create_verification(self.order.unique_reference)
        for i in range(0, document_count):
            verification_document_data = {
                'verification': verification,
                'document_status': 'PENDING',
                'document_type': DocumentType.objects.get(name=doc_types[i])
            }
            vd = VerificationDocument(**verification_document_data)
            vd.save()

        self.assertEqual(mock_send_email.call_count, 0,
                         "{} {} {}".format(document_count, doc_types,
                                           doc_statuses))
        verification = Verification.objects.latest('pk')
        verification_docs = verification.verificationdocument_set.all()
        for i in range(0, verification_docs.count()):
            verification_doc = verification_docs[i]
            verification_doc.document_status = doc_statuses[i]
            verification_doc.save()
        self.assertEqual(mock_send_email.call_count, expected_send_email_count,
                         "{} {} {}".format(document_count, doc_types,
                                           doc_statuses))
        verification.delete()

    @patch('payments.views.get_client_ip')
    @patch('payments.models.send_email')
    def test_notify_on_tier_upgrade(self, mock_send_email, get_client_ip):
        get_client_ip.return_value = \
            settings.SAFE_CHARGE_ALLOWED_DMN_IPS[1].split('-')[0]
        order = self._create_order_api()
        card_id = self.generate_txn_id()
        name = 'Sir Testalot'
        params = self._get_dmn_request_params_for_order(order, card_id,
                                                        name)
        url = reverse('payments.listen_safe_charge')
        self.client.post(url, data=params)
        kyc = self._create_kyc(order.unique_reference)
        docs = kyc.verificationdocument_set.all()
        id_doc = docs.get(document_type__name='ID')
        util_doc = docs.get(document_type__name='UTIL')
        selfie = docs.get(document_type__name='SELFIE')
        whitelist_selfie = docs.get(document_type__name='WHITELIST_SELFIE')
        pref = order.payment_set.get().payment_preference
        # id OK, util PENDING, selfie PENDING
        id_doc.document_status = id_doc.OK
        id_doc.save()
        pref.refresh_from_db()
        self.assertFalse(pref.is_verified)
        self.assertEqual(pref.tier.level, 0)
        # id OK, util OK, selfie PENDING
        util_doc.document_status = id_doc.OK
        util_doc.save()
        pref.refresh_from_db()
        self.assertTrue(pref.is_verified)
        self.assertEqual(pref.tier.level, 1)
        self.assertEqual(mock_send_email.call_count, 1)
        # downgrade to tier 0
        util_doc.document_status = id_doc.PENDING
        util_doc.save()
        pref.refresh_from_db()
        self.assertEqual(pref.tier.level, 0)
        self.assertEqual(mock_send_email.call_count, 1)
        # upgrade to tier1
        util_doc.document_status = id_doc.OK
        util_doc.save()
        pref.refresh_from_db()
        self.assertEqual(pref.tier.level, 1)
        self.assertEqual(mock_send_email.call_count, 2)
        # id OK, util OK, selfie OK
        selfie.document_status = id_doc.OK
        selfie.save()
        pref.refresh_from_db()
        self.assertTrue(pref.is_verified)
        self.assertEqual(pref.tier.level, 2)
        self.assertEqual(mock_send_email.call_count, 3)
        # id OK, util OK, selfie OK, whitelist_selfie OK
        self.assertNotIn(order.withdraw_address, pref.whitelisted_addresses)
        whitelist_selfie.document_status = id_doc.OK
        whitelist_selfie.save()
        pref.refresh_from_db()
        self.assertTrue(pref.is_verified)
        self.assertEqual(pref.tier.level, 3)
        self.assertEqual(mock_send_email.call_count, 4)
        self.assertEqual(whitelist_selfie.whitelisted_address,
                         order.withdraw_address)
        self.assertIn(order.withdraw_address, pref.whitelisted_addresses)

    @patch('payments.models.send_email')
    def test_dont_notify_user_without_email(self, mock_send_email):
        self.order.user.email = ''
        self.order.user.save()
        verification = self._create_verification(self.order.unique_reference)
        verification_document_data = {
            'verification': verification,
            'document_status': 'PENDING',
            'document_type': DocumentType.objects.get(name='ID')
        }
        vd = VerificationDocument(**verification_document_data)
        vd.save()
        self.assertEqual(mock_send_email.call_count, 0)
        verification = Verification.objects.latest('pk')
        verification_docs = verification.verificationdocument_set.all()
        for doc in verification_docs:
            doc.document_status = doc.REJECTED
            doc.save()
        self.assertEqual(mock_send_email.call_count, 0)

    @data_provider(
        lambda: (
            (0, 2, [
                (1, [['UTIL'], ['PENDING']]),
                (1, [['ID'], ['PENDING']])
            ]),
            (0, 2, [
                (1, [['UTIL'], ['PENDING']]),
                (1, [['UTIL'], ['REJECTED']]),
            ]),
            (1, 2, [
                (1, [['UTIL'], ['REJECTED']]),
                (1, [['UTIL'], ['REJECTED']]),
            ]),
            (0, 2, [
                (1, [['UTIL'], ['OK']]),
                (1, [['UTIL'], ['REJECTED']]),
            ]),
            (0, 2, [
                (1, [['UTIL'], ['PENDING']]),
                (1, [['UTIL'], ['REJECTED']]),
            ]),
            (0, 2, [
                (2, [['UTIL', 'ID'], ['PENDING', 'REJECTED']]),
                (2, [['UTIL', 'ID'], ['REJECTED', 'PENDING']]),
            ]),
            (0, 2, [
                (2, [['ID', 'ID'], ['REJECTED', 'REJECTED']]),
                (1, [['ID'], ['PENDING']]),
            ]),
            (1, 2, [
                (1, [['SELFIE'], ['REJECTED']]),
                (1, [['ID'], ['OK']]),
            ]),
            (0, 2, [
                (2, [['ID', 'UTIL'], ['REJECTED', 'REJECTED']]),
                (1, [['SELFIE'], ['PENDING']]),
            ]),
            (1, 2, [
                (2, [['ID', 'UTIL'], ['REJECTED', 'REJECTED']]),
                (1, [['SELFIE'], ['OK']]),
            ]),
            (1, 2, [
                (2, [['ID', 'UTIL'], ['REJECTED', 'OK']]),
                (1, [['SELFIE'], ['OK']]),
            ]),
            (0, 3, [
                (2, [['ID', 'UTIL'], ['REJECTED', 'REJECTED']]),
                (1, [['SELFIE'], ['OK']]),
                (1, [['SELFIE'], ['PENDING']]),
            ]),
        )
    )
    @patch('payments.models.send_email')
    def test_payment_pref_has_couple_verifications(self,
                                                   expected_send_email_count,
                                                   verifications_count,
                                                   verifications_array,
                                                   mock_send_email):
        for verification in verifications_array:
            order = self._create_order_api()
            payment_data = {
                'order': order, 'currency': order.pair.quote,
                'amount_cash': order.amount_quote,
                'payment_preference': self.pref,
                'type': 'D'
            }
            order.register_deposit(payment_data, crypto=False)
            ver = self._create_verification(order.unique_reference)
            payment_pref = ver.payment_preference
            document_count = verification[0]
            documents = verification[1]
            for i in range(0, document_count):
                doc_type = documents[0][i]
                verification_document_data = {
                    'verification': ver,
                    'document_status': 'PENDING',
                    'document_type': DocumentType.objects.get(name=doc_type),
                }
                doc = VerificationDocument(**verification_document_data)
                doc.payment_preference = payment_pref
                doc.save()

        payment_pref_verifications = payment_pref.verification_set.all()
        for i, verification in enumerate(payment_pref_verifications):
            documents = verifications_array[i][1]
            document_statuses = documents[1]
            actual_documents = verification.verificationdocument_set.all()
            for j, doc in enumerate(actual_documents):
                doc.document_status = document_statuses[j]
                doc.save()
        self.assertEqual(mock_send_email.call_count,
                         expected_send_email_count,
                         "{}".format(verifications_array))
        payment_pref.verification_set.all().delete()

    @patch('payments.models.send_email')
    def test_notify_about_pending_documents(self, mock_send_email):
        ver = self._create_verification(self.order.unique_reference)
        payment_pref = ver.payment_preference
        verification_document_data = {
            'verification': ver,
            'document_type': DocumentType.objects.get(name='ID'),
        }
        doc = VerificationDocument(**verification_document_data)
        doc.payment_preference = payment_pref
        doc.save()
        check_kyc_pending_documents_periodic()
        self.assertEqual(mock_send_email.call_count, 0)
        # PENDING document 1 day long
        doc.created_on = datetime.now() - timedelta(days=1)
        doc.save()
        check_kyc_pending_documents_periodic()
        self.assertEqual(mock_send_email.call_count, 1)

    @data_provider(
        lambda: (('Under 18', CategoryRule.LESS, 'persons_age', '18'),)
    )
    def test_flag_kyc_under_18(self, name, rule_type, key, value):
        category_rule, _ = CategoryRule.objects.get_or_create(
            name=name, rule_type=rule_type, key=key, value=value
        )
        category, _ = VerificationCategory.objects.get_or_create(
            name=category_rule.name, flagable=True
        )
        category.rules.add(category_rule)
        category.save()
        ver = self._create_verification(self.order.unique_reference)
        payment_pref = ver.payment_preference
        first_verification_document_data = {
            'verification': ver,
            'document_type': DocumentType.objects.get(name='ID'),
            'birth_date': '2018-08-18'
        }
        first_doc = VerificationDocument(**first_verification_document_data)
        first_doc.payment_preference = payment_pref
        first_doc.save()
        self.assertEqual(ver.category.get(name=category.name), category)

    def test_flag_birth_date_mismatch(self):
        ver = self._create_verification(self.order.unique_reference)
        payment_pref = ver.payment_preference
        first_verification_document_data = {
            'verification': ver,
            'document_type': DocumentType.objects.get(name='ID'),
            'birth_date': '2018-08-18'
        }
        first_doc = VerificationDocument(**first_verification_document_data)
        first_doc.payment_preference = payment_pref
        first_doc.save()
        second_verification_document_data = {
            'verification': ver,
            'document_type': DocumentType.objects.get(name='ID'),
            'birth_date': '1998-07-18'
        }
        second_doc = VerificationDocument(**second_verification_document_data)
        second_doc.payment_preference = payment_pref
        second_doc.save()
        ver.category.get(name='Birth dates not matching')

    @data_provider(
        lambda: (
            ('Surpassed 1000 USD', CategoryRule.MORE, 'total_payments_usd',
             '1000'),
            ('Surpassed 25000 USD', CategoryRule.MORE, 'total_payments_usd',
             '25000'),
            ('Is 100000 USD', CategoryRule.EQUAL, 'total_payments_usd',
             '100000'),
        )
    )
    @patch('payments.models.PaymentPreference.get_successful_payments_amount')
    def test_flag_kyc_on_total_payments_usd_rule(
            self, name, rule_type, key, value, mock_successful_payments_amount
    ):
        category_rule, _ = CategoryRule.objects.get_or_create(
            name=name, rule_type=rule_type, key=key, value=value
        )
        category, _ = VerificationCategory.objects.get_or_create(
            name=category_rule.name, flagable=True
        )

        if rule_type == CategoryRule.MORE:
            mock_successful_payments_amount.return_value = \
                Decimal(value) + Decimal('1')
        elif rule_type == CategoryRule.EQUAL:
            mock_successful_payments_amount.return_value = Decimal(value)

        category.rules.add(category_rule)
        category.save()
        ver = self._create_verification(self.order.unique_reference)
        payment_pref = ver.payment_preference
        first_verification_document_data = {
            'verification': ver,
            'document_type': DocumentType.objects.get(name='ID'),
            'birth_date': '1995-08-18'
        }
        self.order.amount_quote = Decimal(value) + Decimal('1')
        self.order.save()

        first_doc = VerificationDocument(**first_verification_document_data)
        first_doc.payment_preference = payment_pref
        first_doc.save()
        self.assertEqual(ver.category.get(name=category.name), category)
