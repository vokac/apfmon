from django.contrib import admin

from atl.mon.models import State
from atl.mon.models import Factory
from atl.mon.models import Job
from atl.mon.models import Label
from atl.mon.models import Pandaid
from atl.mon.models import Message

class JobAdmin(admin.ModelAdmin):
    list_display = (
                    'cid',
                    'last_modified',
                    'fid',
                    'state',
                    'result',
                    'pandaq',
                   )

class MessageAdmin(admin.ModelAdmin):
    list_display = (
                    'job',
                    'received',
                    'client',
                    'msg',
                   )

class LabelAdmin(admin.ModelAdmin):
    list_display = (
                    'name',
                    'fid',
                    'msg',
                    'last_modified',
                   )

class FactoryAdmin(admin.ModelAdmin):
    list_display = (
                    'name',
                    'email',
                    'last_startup',
                    'last_ncreated',
                    'last_modified',
                   )

admin.site.register(State)
admin.site.register(Factory, FactoryAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(Pandaid)
admin.site.register(Message, MessageAdmin)
admin.site.register(Label, LabelAdmin)
