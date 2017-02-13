from django.contrib import admin

from ticker.models import Price, Ticker

admin.site.register(Ticker)
admin.site.register(Price)

admin.autodiscover()
