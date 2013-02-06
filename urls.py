from django.conf.urls.defaults import *
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    (r'^$', include('atl.mon.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^kit/', include('atl.kit.urls')),
    (r'^api/', include('atl.api.urls')),
    (r'^mon/', include('atl.mon.urls')),
)

urlpatterns += staticfiles_urlpatterns()
