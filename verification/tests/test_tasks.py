from unittest.mock import patch
from core.tests.base import OrderBaseTestCase, VerificationBaseTestCase
from core.tests.utils import data_provider
from verification.models import Verification, VerificationDocument, \
    DocumentType
from payments.models import PaymentPreference
from orders.models import Order
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from django.test.utils import freeze_time
from datetime import timedelta, datetime
from verification.task_summary import check_kyc_pending_documents_periodic


class VerificationStatusesTestCase(OrderBaseTestCase,
                                   VerificationBaseTestCase):

    def setUp(self):
        super(VerificationStatusesTestCase, self).setUp()

        self.api_client = APIClient()
        self.pref = PaymentPreference.objects.get(
            payment_method__name='Safe Charge'
        )
        django_friendly_file = self._create_image()
        payment_pref = PaymentPreference.objects.latest('pk')
        self.user.email = payment_pref.user.email
        self.user.save()
        self.verification_data = {
            'payment_preference': payment_pref
        }

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
        verification = Verification(**self.verification_data,
                                    user=self.user)
        verification.save()
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
        from accounts.models import User
        user_without_email = User.objects.get(username='AnonymousUser')
        payment_pref = PaymentPreference.objects.latest('pk')
        payment_pref.user = user_without_email
        payment_pref.save()
        verification_data = self.verification_data
        verification_data['payment_preference'] = payment_pref
        verification = Verification(**verification_data,
                                    user=user_without_email,
                                    )
        verification.save()
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
        payment_pref = PaymentPreference.objects.latest('pk')
        for verification in verifications_array:
            ver = Verification(**self.verification_data, user=self.user)
            ver.save()
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
        payment_pref = PaymentPreference.objects.latest('pk')
        ver = Verification(**self.verification_data, user=self.user)
        ver.save()
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
