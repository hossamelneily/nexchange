import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import models

from core.common.models import SoftDeletableModel, TimeStampedModel


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
    OG_FIELDS = ['title', 'description', 'image']
    resource_url = models.CharField(max_length=255,
                                    null=False, blank=False)
    image = models.CharField(max_length=255, default=None,
                             blank=True)
    title = models.CharField(max_length=255, default=None,
                             blank=True)
    site_name = models.CharField(max_length=255, default=None,
                                 blank=True)
    description = models.CharField(max_length=500, default=None,
                                   blank=True)
    page = models.ForeignKey(CmsPage,
                             default=None,
                             related_name='resources_sets',
                             on_delete=models.CASCADE)
    use_og = models.BooleanField(default=True)

    def convert_og_to_props(self):
        res = requests.get(self.resource_url)
        soup = BeautifulSoup(res.content, 'html.parser')

        for prop in OgResource.OG_FIELDS:
            key_attr = 'og:{}'.format(prop)
            elem = soup.findAll('meta', {'name': key_attr})
            if len(elem) and hasattr(elem[0], 'content'):
                content = elem[0]['content']
                setattr(self, prop, content)
        self.use_og = False

    @property
    def short_domain(self):
        fragments = self.resource_url.split('.')
        relevant_part = '.'.join(fragments[-2:])
        relevant_part = relevant_part.split('/')[0]
        return relevant_part

    def save(self, *args, **kwargs):
        if self.use_og:
            self.convert_og_to_props()

        super(OgResource, self).save(*args, **kwargs)

    def __str__(self):
        return '{} (Page: {})'.format(self.short_domain,
                                      self.page)
