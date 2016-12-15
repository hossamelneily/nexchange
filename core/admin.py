from django.contrib import admin
from djcelery.models import TaskMeta


class TaskMetaAdmin(admin.ModelAdmin):
    readonly_fields = ('result',)


admin.autodiscover()
admin.site.register(TaskMeta, TaskMetaAdmin)
