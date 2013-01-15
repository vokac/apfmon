from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # rendered web pages
    (r'^$', include('atl.mon.urls')),
    (r'^mon/', include('atl.mon.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^kit/', include('atl.kit.urls')),
    # maybe apfmon API as separate app
#    (r'^api/', include('atl.api.urls')),
#    python manage.py startapp api
)
