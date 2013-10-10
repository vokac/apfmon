from django.conf.urls import patterns
#from django.views.generic import list_detail
#from django.views.generic.date_based import archive_index

urlpatterns = patterns('apfmon.kit.views',

# non-rendered views
    (r'^q/$', 'pandaqueues'),
    (r'^update/$', 'update'),
)
