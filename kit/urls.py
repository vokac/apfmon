from django.conf.urls.defaults import *
#from django.views.generic import list_detail
#from django.views.generic.date_based import archive_index

urlpatterns = patterns('atl.kit.views',

# non-rendered views
#    (r'^n/(?P<state>[A-Z]*)/?(?P<qid>\d*)$', 'count'),
#    (r'^ping/(?P<tag>\S*)/?$', 'ping'),
#    (r'^rn/(?P<cid>\S*)/$', 'rn'),
#    (r'^ex/(?P<cid>\S*)/(?P<sc>\d*)$', 'ex'),
#    (r'^cid/$', 'cid'),
#    (r'^old/$', 'old'),
#    (r'^awol/$', 'awol'),
#    (r'^flag/$', 'flag'),
    (r'^q/$', 'pandaqueues'),
    (r'^update/$', 'update'),
#    (r'^s/$', 'pandasites'),
#    (r'^r/$', 'rrd'),

)
