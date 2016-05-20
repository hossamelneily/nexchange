"""nexchange URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
import core.views
from core.models import Currency, Profile

admin.site.register(Currency)
admin.site.register(Profile)


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', core.views.main, name='main'),
 #   url(r'^order/$',  core.views.add_order),
    url(r'^order/add/$', core.views.add_order),

]
