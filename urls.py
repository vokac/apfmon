from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    (r'^$', include('atl.mon.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^mon/', include('atl.mon.urls')),
    (r'^kit/', include('atl.kit.urls')),
)
