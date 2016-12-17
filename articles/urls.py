from django.conf.urls import url
from articles import views

article_urls = [
    url(r'^(?P<page_name>.+)/$', views.cms_page,
        name='articles.cms_page'),
]
