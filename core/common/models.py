from django.conf import settings
from django.db import models
from safedelete import (DELETED_INVISIBLE, DELETED_VISIBLE_BY_PK, SOFT_DELETE,
                        safedelete_manager_factory, safedelete_mixin_factory)

SoftDeleteMixin = safedelete_mixin_factory(policy=SOFT_DELETE,
                                           visibility=DELETED_VISIBLE_BY_PK)


class UniqueFieldMixin(models.Model):

    class Meta:
        abstract = True

    @staticmethod
    def gen_unique_value(val_gen, set_len_gen, start_len):
        failed_count = 0
        max_len = start_len
        while True:
            if failed_count >= \
                    settings.REFERENCE_LOOKUP_ATTEMPTS:
                failed_count = 0
                max_len += 1

            val = val_gen(max_len)
            cnt_unq = set_len_gen(val)
            if cnt_unq == 0:
                return val
            else:
                failed_count += 1


class SoftDeletableModel(SoftDeleteMixin):
    disabled = models.BooleanField(default=False)
    active_objects = safedelete_manager_factory(
        models.Manager, models.QuerySet, DELETED_INVISIBLE)()

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class IpAwareModel(TimeStampedModel, SoftDeleteMixin):
    ip = models.CharField(max_length=39,
                          null=True,
                          default=None)

    class Meta:
        abstract = True
