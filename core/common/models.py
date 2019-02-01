from django.conf import settings
from django.db import models
import binascii
import os
from safedelete import (DELETED_INVISIBLE, DELETED_VISIBLE_BY_PK, SOFT_DELETE,
                        safedelete_manager_factory, safedelete_mixin_factory)
from django.utils.crypto import get_random_string
from random import randint
from django.contrib.postgres.fields import JSONField
import json

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


class UniqueFieldMixin:

    def get_random_unique_reference(self, x):
        return get_random_string(x)

    def gen_unique_payment_id(self, length):
        bytes_payment_id = binascii.hexlify(os.urandom(length))
        return bytes_payment_id.decode("utf-8")

    def get_random_integer(self):
        return randint(0, 2**32 - 1)

    def gen_destination_tag(self, generate_integer,
                            get_objects_amount_by_tag):
        while True:
            value = generate_integer()
            count_repetitive = get_objects_amount_by_tag(value)
            if count_repetitive == 0:
                return value
            else:
                continue

    def gen_unique_value(self, generate_string,
                         get_objects_amount_by_ref,
                         start_len):
        failed_count = 0
        max_len = start_len
        prefix = self.__class__.__name__[:1]
        while True:
            if failed_count >= \
                    settings.REFERENCE_LOOKUP_ATTEMPTS:
                failed_count = 0
                max_len += 1

            value = (prefix + generate_string(max_len)).upper()
            count_repetitive = get_objects_amount_by_ref(value)
            if count_repetitive == 0:
                return value
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


class NamedModel(models.Model):
    name = models.CharField(null=True, blank=True, max_length=255)

    def __str__(self):
        return '{}'.format(self.name)

    class Meta:
        abstract = True


class IndexTimeStampedModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, db_index=True)
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
    flag_val = models.TextField(default=None, null=True, blank=True)
    model_name = models.CharField(default=None, max_length=255)
    flagged_id = models.PositiveIntegerField(default=None)

    def __str__(self):
        return '{} pk {} ({})'.format(self.model_name, self.flagged_id,
                                      self.flag_val)


class FlagableMixin(models.Model):

    class Meta:
        abstract = True

    def flag(self, val=None):
        if not self.flagged:
            self.flagged = True
            self.save()
        return Flag.objects.get_or_create(
            model_name=self.__class__.__name__,
            flagged_id=self.pk,
            flag_val=val
        )

    flagged = models.BooleanField(default=False)

    @property
    def flags(self):
        return Flag.objects.filter(
            model_name=self.__class__.__name__,
            flagged_id=self.pk
        )


class RequestLog(IpAwareModel):

    class Meta:
        abstract = True

    url = models.TextField(null=True, blank=True)
    response = models.TextField(null=True, blank=True)
    payload = models.TextField(null=True, blank=True)
    payload_json = JSONField(null=True, blank=True)

    def get_payload_dict(self):
        res = self.payload_json
        if settings.DATABASES.get(
                'default', {}).get('ENGINE') == 'django.db.backends.sqlite3':
            if isinstance(self.payload, dict):
                res = self.payload
            elif isinstance(self.payload, str):
                json_str = self.payload.replace("'", "\"")
                res = json.loads(json_str) if json_str else {}
        return res if res else {}

    def set_payload(self, payload):
        if settings.DATABASES.get(
                'default', {}).get('ENGINE') == 'django.db.backends.sqlite3':
            self.payload = payload
        else:
            self.payload_json = payload
