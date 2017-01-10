from django.contrib import admin


class TaskMetaAdmin(admin.ModelAdmin):
    readonly_fields = ('result',)


admin.autodiscover()
