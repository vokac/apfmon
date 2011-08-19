from django.conf.urls.defaults import *
#from django.views.generic import list_detail
#from django.views.generic.date_based import archive_index

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('atl.mon.views',
# rendered views
#    (r'^$', 'offline'),
    (r'^$', 'index'),
    (r'^cloud/(?P<name>[a-zA-Z]*)/?$', 'cloud'),
    (r'^factory/(?P<fid>\S*)/?$', 'factory'),
#    (r'^t/?$', 'total'),
    (r'^queues/?$', 'queues'),
    (r'^history/(?P<qid>\d*)/?$', 'history'),
    (r'^info/?$', 'info'),
    (r'^q/(?P<qid>\d*)/page/(?P<p>\d*)$', 'pandaq'),
    (r'^q/(?P<qid>\d*)/+$', 'pandaq'),
    (r'^job/(?P<fid>\S*)/(?P<cid>\S*)/?$', 'job'),
    (r'^jobs/(?P<lid>\d*)/(?P<state>[A-Z]*)/page/(?P<p>\d*)$', 'jobs'),
    (r'^jobs/(?P<lid>\d*)/(?P<state>[A-Z]*)/?$', 'jobs'),
    # these rrd time periods: 1h 6h 1d 1w 1m 1y
#    (r'^img/states-(?P<t>\d[hdwmy])-(?P<fid>\d*)-(?P<qid>\d*).png$', 'img'),
    (r'^debug/$', 'debug'),
    (r'^test/$', 'test'),

# non-rendered views
    (r'^c/$', 'cr2'),
    (r'^f/$', 'fids'),
    (r'^h/$', 'helo'),
    (r'^i/(?P<fid>\S*)/(?P<cid>\S*)/$', 'info'),
    (r'^m/$', 'msg'),
    (r'^n/(?P<fid>\d*)/(?P<state>[A-Z]*)/?(?P<qid>\d*)$', 'count'),
    (r'^r/$', 'rrd'),
    (r'^cr/$', 'cr'),
    (r'^ex/(?P<fid>\S*)/(?P<cid>\S*)/(?P<sc>\d*)$', 'ex'),
    (r'^st/$', 'st'),
    (r'^rn/(?P<fid>\S*)/(?P<cid>\S*)/$', 'rn'),
    (r'^cid/(?P<fid>\S*)$', 'cid'),
    (r'^old/(?P<fid>\S*)$', 'old'),
    (r'^msg/$', 'action'),
    (r'^awol/$', 'awol'),
    (r'^stale/$', 'stale'),
    (r'^search/$', 'search'),
    (r'^query/(?P<q>.+)/$', 'query'),
#    (r'^q/$', 'pandaqueues'),
#    (r'^s/$', 'pandasites'),

# admin interface
    (r'^admin/(.*)', admin.site.root),

)


"""
django.views.generic.date_based.archive_index
http://docs.djangoproject.com/en/dev/ref/generic-views/
"""
