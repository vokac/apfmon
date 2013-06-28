from django.conf.urls import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^kit/', include('apfmon.kit.urls')),
    (r'^api/', include('apfmon.api.urls')),
    (r'^', include('apfmon.mon.urls')),
)

urlpatterns += staticfiles_urlpatterns()
