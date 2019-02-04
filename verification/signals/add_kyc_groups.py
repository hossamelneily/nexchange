from django.db.models.signals import post_save
from django.dispatch import receiver
from verification.models import Verification, VerificationCategory,\
    CategoryRule
from decimal import Decimal, InvalidOperation


def raw_add_kyc_groups(instance):
    if not instance or not instance.payment_preference:
        return
    pref = instance.payment_preference
    used_categs = VerificationCategory.objects.filter(
        verification__in=[instance]
    )
    birth_date_not_matching_categ, _ = VerificationCategory.objects. \
        get_or_create(name='Birth dates not matching', flagable=True)
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

    # Adding categories based on payment preference payload
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

    # Adding category if birth dates are not matching
    # or removing it if category used and birth dates are matching
    if birth_date_not_matching_categ in unused_categs and \
            not pref.birth_dates_matching():
        instance.category.add(birth_date_not_matching_categ)
    elif birth_date_not_matching_categ in used_categs and \
            pref.birth_dates_matching():
        instance.category.remove(birth_date_not_matching_categ)

    # Adding category if value of the rule is numeric and payment pref
    # or verification has the attribute == rule.key
    rule_categs = unused_categs.filter(rules__isnull=False)
    for categ in rule_categs:
        for rule in categ.rules.all():
            rule_key = rule.key
            obj = None
            if hasattr(instance, rule_key):
                obj = instance
            elif hasattr(pref, rule_key):
                obj = pref
            if obj is not None:
                obj_attribute_value = getattr(obj, rule_key)
                try:
                    rule_value = Decimal(rule.value)
                    if rule.rule_type == CategoryRule.LESS \
                            and Decimal(obj_attribute_value) < rule_value:
                        instance.category.add(categ)
                    elif rule.rule_type == CategoryRule.EQUAL \
                            and Decimal(obj_attribute_value) == rule_value:
                        instance.category.add(categ)
                    elif rule.rule_type == CategoryRule.MORE \
                            and Decimal(obj_attribute_value) > rule_value:
                            instance.category.add(categ)
                except (InvalidOperation, TypeError):
                    continue
            else:
                continue


@receiver(post_save, sender=Verification)
def add_kyc_groups(sender, instance=None, **kwargs):
    raw_add_kyc_groups(instance)
