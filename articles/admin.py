from django.contrib import admin
from articles.models import CmsPage, OgResource

admin.site.register(CmsPage)
admin.site.register(OgResource)

admin.autodiscover()
