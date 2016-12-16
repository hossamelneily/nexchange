from django.contrib import admin
from articles.models import CmsPage

admin.site.register(CmsPage)

admin.autodiscover()
