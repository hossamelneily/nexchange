from django.conf.urls import url

from verification.views import views


verification_urls = [
    url(r'^$', views.Upload.as_view(), name='verification.upload'),
    url(r'^download/(?P<file_name>.*)/$', views.download,
        name='verification.download'),
]
