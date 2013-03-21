from django.conf.urls.defaults import *
#from django.views.generic import list_detail
#from django.views.generic.date_based import archive_index

urlpatterns = patterns('apfmon.mon.views',
# rendered views
#    (r'^$', 'offline'),
    (r'^$', 'index'),
    (r'^clouds/?$', 'cloudindex'),
    (r'^cloud/(?P<name>[a-zA-Z]+)/?$', 'cloud'),
    (r'^factory/(?P<fid>\S*)/?$', 'factory'),
#    (r'^t/?$', 'total'),
    (r'^queues/?$', 'queues'),
    (r'^l/(?P<lid>\d*)/page/(?P<p>\d*)$', 'label'),
    (r'^l/(?P<lid>\d*)/+$', 'label'),
    (r'^labels/?$', 'labels'),
    (r'^fault/?$', 'fault'),
    (r'^site/(?P<sid>\d*)$', 'site'),
    (r'^history/(?P<qid>\d*)/?$', 'history'),
    (r'^help/?$', 'help'),
    (r'^q/(?P<qid>\d*)/page/(?P<p>\d*)$', 'pandaq'),
    (r'^q/(?P<qid>\d*)/+$', 'pandaq'),
    (r'^job1/(?P<fid>\S*)/(?P<cid>\S*)/?$', 'job1'),
    (r'^jobs1/(?P<lid>\d*)/(?P<state>[A-Z]*)/page/(?P<p>\d*)$', 'jobs1'),
    (r'^jobs1/(?P<lid>\d*)/(?P<state>[A-Z]*)/?$', 'jobs1'),
    # these rrd time periods: 1h 6h 1d 1w 1m 1y
#    (r'^img/states-(?P<t>\d[hdwmy])-(?P<fid>\d*)-(?P<qid>\d*).png$', 'img'),
    (r'^debug/$', 'debug'),
    (r'^test/$', 'test'),
    (r'^stats/$', 'stats'),

# non-rendered views
    (r'^c/$', 'cr'),
    (r'^f/$', 'fids'),
    (r'^h/$', 'helo'),
#    (r'^i/(?P<fid>\S*)/(?P<cid>\S*)/$', 'info'),
    (r'^m/$', 'msg'),
    (r'^n/(?P<fid>\d*)/(?P<state>[A-Z]*)/?(?P<qid>\d*)$', 'count'),
    (r'^r/$', 'rrd'),
#    (r'^cr/$', 'cr'),
    (r'^ex/(?P<fid>\S*)/(?P<cid>\S*)/(?P<sc>\d*)$', 'ex'),
    (r'^st/$', 'st'),
    (r'^rn/(?P<fid>\S*)/(?P<cid>\S*)/$', 'rn'),
    (r'^cid/(?P<fid>\S*)$', 'cid'),
    (r'^old/(?P<fid>\S*)$', 'old'),
    (r'^msg/$', 'action'),
    (r'^awol/$', 'awol'),
    (r'^stale/$', 'stale'),
    (r'^search/$', 'search'),
    (r'^query/(?P<q>.*)/$', 'query'),

)


"""
django.views.generic.date_based.archive_index
http://docs.djangoproject.com/en/dev/ref/generic-views/
"""
