from django.conf.urls import patterns

urlpatterns = patterns('apfmon.mon.views',
    (r'^$', 'index'),
# rendered views
    (r'^cloud/(?P<name>[a-zA-Z]+)/?$', 'cloud'),
    (r'^report/?$', 'report'),
    (r'^site/(?P<sid>\S*)$', 'site'),
    (r'^help/?$', 'help'),
    (r'^q/(?P<qid>\d*)/page/(?P<p>\d*)$', 'pandaq'),
    (r'^q/(?P<qid>\S*)/?$', 'pandaq'),
    (r'^debug/?$', 'debug'),
    (r'^testindex/?$', 'testindex'),
    (r'^stats/?$', 'stats'),  #to be removed
    (r'^test500/?$', 'test500'),

# non-rendered views
    (r'^search/$', 'search'),
    (r'^query/(?P<q>.*)/$', 'query'),

# human ui, note these are basically a catchall pattern
    (r'(?P<fname>[\w-]*)/(?P<item>\S*[^/])$', 'singleitem'),
    (r'(?P<fname>[\w-]*)$', 'singlefactory'),
)
