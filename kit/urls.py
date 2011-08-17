from django.conf.urls.defaults import *
#from django.views.generic import list_detail
#from django.views.generic.date_based import archive_index

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('atl.kit.views',
# rendered views
    (r'^$', 'index'),

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

# admin interface
    (r'^admin/(.*)', admin.site.root),

)
