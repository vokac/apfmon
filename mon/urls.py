from django.conf.urls import patterns

urlpatterns = patterns('apfmon.mon.views',
    (r'^$', 'index'),
# rendered views
    (r'^cloud/(?P<name>[a-zA-Z]+)/?$', 'cloud'),
    (r'^factory/(?P<fid>\S*)/?$', 'factory'),
    (r'^queues/?$', 'queues'),
    (r'^l/(?P<lid>\d*)/page/(?P<p>\d*)$', 'label'),
    (r'^l/(?P<lid>\d*)/+$', 'label'),
    (r'^report/?$', 'report'),
    (r'^site/(?P<sid>\S*)$', 'site'),
    (r'^help/?$', 'help'),
    (r'^q/(?P<qid>\d*)/page/(?P<p>\d*)$', 'pandaq'),
    (r'^q/(?P<qid>\S*)/+$', 'pandaq'),
    (r'^job1/(?P<fid>\S*)/(?P<cid>\S*)/?$', 'job1'),
    (r'^jobs1/(?P<lid>\d*)/(?P<state>[A-Z]*)/page/(?P<p>\d*)$', 'jobs1'),
    (r'^jobs1/(?P<lid>\d*)/(?P<state>[A-Z]*)/?$', 'jobs1'),
    (r'^debug/$', 'debug'),
    (r'^test/$', 'test'),
    (r'^stats/$', 'stats'),
# human ui, note these are basically a catchall pattern
    (r'(?P<fname>[\w-]*)/(?P<item>\S*)/?$', 'singleitem'),
    (r'(?P<fname>[\w-]*)/?$', 'singlefactory'),

# non-rendered views
    (r'^c/$', 'cr'),
    (r'^h/$', 'helo'),
    (r'^m/$', 'msg'),
    (r'^ex/(?P<fid>\S*)/(?P<cid>\S*)/(?P<sc>\d*)$', 'ex'),
    (r'^rn/(?P<fid>\S*)/(?P<cid>\S*)/$', 'rn'),
    (r'^msg/$', 'action'),
    (r'^search/$', 'search'),
    (r'^query/(?P<q>.*)/$', 'query'),

)

"""
django.views.generic.date_based.archive_index
http://docs.djangoproject.com/en/dev/ref/generic-views/
"""
