from django.conf.urls.defaults import *
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    (r'^mon/', include('apfmon.mon.urls')),
    (r'^', include('apfmon.mon.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^kit/', include('apfmon.kit.urls')),
    (r'^api/', include('apfmon.api.urls')),
)

urlpatterns += staticfiles_urlpatterns()
