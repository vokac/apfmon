# https://docs.djangoproject.com/en/1.10/topics/http/urls/
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
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
