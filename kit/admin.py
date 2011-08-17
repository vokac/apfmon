from django.contrib import admin

from atl.kit.models import Tag
from atl.kit.models import Site
from atl.kit.models import Cloud
from atl.kit.models import PandaQueue
from atl.kit.models import PandaSite

class PandaQueueAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'pandasite',
                    'state',
                    'comment',
                   )

admin.site.register(Tag)
admin.site.register(Site)
admin.site.register(Cloud)
admin.site.register(PandaQueue, PandaQueueAdmin)
admin.site.register(PandaSite)
