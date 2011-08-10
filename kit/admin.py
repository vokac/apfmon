from django.contrib import admin

from atl.kit.models import Tag
from atl.kit.models import Site
from atl.kit.models import Cloud
from atl.kit.models import PandaQueue
from atl.kit.models import PandaSite
from atl.kit.models import Queue
from atl.kit.models import Comment

class CommentAdmin(admin.ModelAdmin):
    list_display = ('site',
                    'received',
                    'client',
                    'msg',
                    'dn',
                   )

admin.site.register(Tag)
admin.site.register(Site)
admin.site.register(Cloud)
admin.site.register(PandaQueue)
admin.site.register(PandaSite)
admin.site.register(Queue)
admin.site.register(Comment, CommentAdmin)
