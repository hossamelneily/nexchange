from django.db.models.signals import post_save
from django.dispatch import receiver
from nexchange.utils import get_nexchange_logger
from verification.models import VerificationDocument

logger = get_nexchange_logger('notify_verification', True, True)


def doc_status_changed(old_status, new_status):
    return True if old_status != new_status else False


def meets_requirements_for_notification(obj):
    if obj is None or obj.pk is None or obj.kyc_push \
            or obj.document_status not in [obj.REJECTED, obj.OK] \
            or not doc_status_changed(obj.original_document_status,
                                      obj.document_status):
        return False
    ver = obj.verification
    payment_preference = ver.payment_preference if ver else None
    if payment_preference is None or payment_preference.user_email is None \
            or not payment_preference._has_pending_orders:
        return False
    if any([payment_preference.has_pending_documents]):
        return False
    if obj.document_status == obj.REJECTED:
        if payment_preference.get_payment_preference_document_status(
                obj.document_type.name) == 'OK':
            return False
    return True


@receiver(post_save, sender=VerificationDocument)
def notify_document_was_rejected(sender, instance=None, **kwargs):
    try:
        if not meets_requirements_for_notification(instance):
            return
    except AttributeError:
        return
    ver = instance.verification
    payment_preference = ver.payment_preference if ver else None
    order_ref = ver.note if ver and ver.note else None
    try:
        rejected_documents = payment_preference.rejected_documents
        if len(rejected_documents) > 0:
            document_quantity = 'document' if len(rejected_documents) == 1 \
                else 'documents'
            was_or_were = 'was' if len(rejected_documents) == 1 else 'were'
            subject = "Your KYC {} {} rejected".format(
                document_quantity, was_or_were
            )
            try_again = \
                ' Try again here https://n.exchange/order/{}/'.format(
                    order_ref) if order_ref else ''
            message = "Your {} {} rejected.{}".format(
                document_quantity, was_or_were, try_again
            )
            email_to = payment_preference.user_email
            payment_preference.notify(email_to, subject, message)
    except Exception as e:
        logger.error('Unable to send order notification. error: {}'.format(e))
