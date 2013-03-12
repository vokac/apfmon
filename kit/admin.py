from django.contrib import admin

from atl.kit.models import Tag
from atl.kit.models import Site
from atl.kit.models import Cloud
from atl.kit.models import BatchQueue
from atl.kit.models import PandaSite

class BatchQueueAdmin(admin.ModelAdmin):
    list_display = (
                    'name',
                    'pandasite',
                    'state',
                    'comment',
                    'timestamp',
                   )

class PandaSiteAdmin(admin.ModelAdmin):
    list_display = (
                    'name',
                    'site',
                    'tier',
                    )
admin.site.register(Tag)
admin.site.register(Site)
admin.site.register(Cloud)
admin.site.register(BatchQueue, BatchQueueAdmin)
admin.site.register(PandaSite, PandaSiteAdmin)
