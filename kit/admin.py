from django.contrib import admin

from apfmon.kit.models import Site
from apfmon.kit.models import BatchQueue
from apfmon.kit.models import WMSQueue

class BatchQueueAdmin(admin.ModelAdmin):
    list_display = (
                    'name',
                    'wmsqueue',
                    'state',
                    'comment',
                    'timestamp',
                   )

class WMSQueueAdmin(admin.ModelAdmin):
    list_display = (
                    'name',
                    'site',
                    )

admin.site.register(Site)
admin.site.register(BatchQueue, BatchQueueAdmin)
admin.site.register(WMSQueue, WMSQueueAdmin)
