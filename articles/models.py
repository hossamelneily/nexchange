from django.db import models
from core.common.models import TimeStampedModel, SoftDeletableModel
from django.conf import settings


class CmsBase(TimeStampedModel, SoftDeletableModel):
    class Meta:
        abstract = True

    all_cms = [a for a in settings.CMSPAGES.values()]
    all_cms = all_cms[0] + all_cms[1]

    t_footers = [(a[0], a[0]) for a in all_cms]

    TYPES = (
        t_footers
    )
    name = models.CharField(default=None, max_length=50, choices=TYPES)
    locale = models.CharField(default=settings.LANGUAGES[0],
                              max_length=2,
                              null=True,
                              choices=settings.LANGUAGES)


class CmsPage(CmsBase):
    head = models.TextField(default=None, null=True)
    written_by = models.TextField(default=None, null=True)
    body = models.TextField(default=None, null=True)

    def __str__(self):
        return "{} - {}".format(self.name, self.locale)


class OgResource(CmsBase):
    resource_url = models.CharField(max_length=255,
                                    null=False, blank=False)
    image = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    site_name = models.CharField(max_length=255)
    body = models.CharField(max_length=500)
    page = models.ForeignKey(CmsPage, default=None)
