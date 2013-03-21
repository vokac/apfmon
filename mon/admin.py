from django.contrib import admin

from apfmon.mon.models import Factory
from apfmon.mon.models import Job
from apfmon.mon.models import Label

class JobAdmin(admin.ModelAdmin):
    list_display = (
                    'cid',
                    'created',
                    'last_modified',
                    'label',
                    'state',
                    'result',
                    'flag',
                   )

class LabelAdmin(admin.ModelAdmin):
    list_display = (
                    'name',
                    'fid',
                    'msg',
                    'last_modified',
                    'resource',
                    'localqueue',
                    'batchqueue',
                   )

class FactoryAdmin(admin.ModelAdmin):
    list_display = (
                    'name',
                    'email',
                    'last_startup',
                    'last_ncreated',
                    'last_modified',
                   )

admin.site.register(Job, JobAdmin)
admin.site.register(Label, LabelAdmin)
admin.site.register(Factory, FactoryAdmin)
