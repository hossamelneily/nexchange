from django.conf import settings
from django.db import models
from safedelete import (DELETED_INVISIBLE, DELETED_VISIBLE_BY_PK, SOFT_DELETE,
                        safedelete_manager_factory, safedelete_mixin_factory)

SoftDeleteMixin = safedelete_mixin_factory(policy=SOFT_DELETE,
                                           visibility=DELETED_VISIBLE_BY_PK)


class NexchangeManager(models.Manager):
    def get_by_natural_key(self, param):
        qs = self.get_queryset()
        lookup = {qs.model.NATURAL_KEY: param}
        return self.get(**lookup)


class NexchangeModel(models.Model):
    class Meta:
        abstract = True
    objects = NexchangeManager()


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
    class Meta:
        abstract = True

    ip = models.CharField(max_length=39,
                          null=True,
                          default=None)


class Flag(TimeStampedModel):
    flag_val = models.CharField(default=None, null=True, blank=True,
                                max_length=255)
    model_name = models.CharField(default=None, max_length=255)
    flagged_id = models.PositiveIntegerField(default=None)

    def __str__(self):
        return '{} pk {} ({})'.format(self.model_name, self.flagged_id,
                                      self.flag_val)


class FlagableMixin(models.Model):

    class Meta:
        abstract = True

    def flag(self, val=None):
        return Flag.objects.get_or_create(
            model_name=self.__class__.__name__,
            flagged_id=self.pk,
            flag_val=val
        )
