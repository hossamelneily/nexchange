from django.conf.urls import url

from support.views import SupportView, ThanksView

support_urls = [
    url(r'^$', SupportView.as_view(), name='support_urls'),
    url(r'^thanks/$', ThanksView.as_view()),
]
