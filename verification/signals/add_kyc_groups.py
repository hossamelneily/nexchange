from django.db.models.signals import post_save
from django.dispatch import receiver
from verification.models import Verification, VerificationCategory,\
    CategoryRule


def raw_add_kyc_groups(instance):
    if not instance or not instance.payment_preference:
        return
    pref = instance.payment_preference
    unused_categs = VerificationCategory.objects.exclude(
        verification__in=[instance]
    )
    if not unused_categs:
        return
    if pref.bank_bin and pref.bank_bin.bank:
        bank_categs = unused_categs.filter(
            banks__in=[instance.payment_preference.bank_bin.bank]
        )
        for cat in bank_categs:
            instance.category.add(cat)
    if pref.push_request and pref.push_request.get_payload_dict():
        rule_categs = unused_categs.filter(rules__isnull=False)
        payload = pref.push_request.get_payload_dict()
        for categ in rule_categs:
            for rule in categ.rules.all():
                kyc_val = payload.get(rule.key)
                if kyc_val:
                    if rule.rule_type == CategoryRule.EQUAL \
                            and kyc_val == rule.value:
                        instance.category.add(categ)
                    elif rule.rule_type == CategoryRule.IN \
                            and rule.value.lower() in kyc_val.lower():
                        instance.category.add(categ)


@receiver(post_save, sender=Verification)
def add_kyc_groups(sender, instance=None, **kwargs):
    raw_add_kyc_groups(instance)
