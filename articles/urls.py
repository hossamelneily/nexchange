from django.urls import re_path

from articles import views

article_urls = [
    re_path(r'^(?P<page_name>.+)/$', views.cms_page,
            name='articles.cms_page'),
]
