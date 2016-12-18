from django.db import models
from django.conf import settings


class CmsPage(models.Model):
    all_cms = [a for a in settings.CMSPAGES.values()]
    all_cms = all_cms[0] + all_cms[1]

    t_footers = [(a[0], a[0]) for a in all_cms]

    TYPES = (
        t_footers
    )

    name = models.CharField(default=None, max_length=50, choices=TYPES)
    head = models.TextField(default=None, null=True)
    written_by = models.TextField(default=None, null=True)
    body = models.TextField(default=None, null=True)
    locale = models.CharField(default=settings.LANGUAGES[0],
                              max_length=2,
                              null=True,
                              choices=settings.LANGUAGES)

    def __str__(self):
        return "{} - {}".format(self.name, self.locale)
