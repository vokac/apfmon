# https://docs.djangoproject.com/en/1.10/topics/http/urls/
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin', admin.site.urls),
    url(r'^kit/', include('kit.urls')),
    url(r'^api/', include('api.urls')),
#    url(r'^mon/', include('mon.urls')),
    url(r'^', include('mon.urls')),
]

urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
