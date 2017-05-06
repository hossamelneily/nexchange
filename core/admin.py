from django.contrib import admin
from core.models import Currency, Transaction, Address, \
    Pair, Location, AddressReserve
from core.common.models import Flag


admin.site.register(AddressReserve)
admin.site.register(Currency)
admin.site.register(Transaction)
admin.site.register(Address)
admin.site.register(Pair)
admin.site.register(Flag)
admin.site.register(Location)
admin.autodiscover()
