from django.conf.urls import url

from . import views

urlpatterns = [
# rendered views
    url(r'^$', views.index, name='index'),
    url(r'^cloud/(?P<name>[a-zA-Z]+)/?$', views.cloud, name='cloud'),
    url(r'^report/?$', views.report, name='report'),
    url(r'^site/(?P<sid>\S*)$', views.site, name='site'),
    url(r'^help/?$', views.help, name='help'),
    url(r'^q/(?P<qid>\S*)/page/(?P<p>\d*)$', views.pandaq, name='pandaq'),
    url(r'^q/(?P<qid>\S*)/?$', views.pandaq, name='pandaq'),
    url(r'^debug/?$', views.debug, name='debug'),
    url(r'^testindex/?$', views.testindex, name='testindex'),
    url(r'^test500/?$', views.test500, name='test500'),

# non-rendered views
    url(r'^search/$', views.search, name='search'),
    url(r'^query/(?P<q>.*)/$', views.query, name='query'),

# human ui, note these are basically a catchall pattern
    url(r'(?P<fname>[\w-]*)/(?P<item>\S*[^/])$', views.singleitem, name='singleitem'),
    url(r'(?P<fname>[-\w.]*)$', views.singlefactory, name='singlefactory'),
]
