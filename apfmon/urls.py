# https://docs.djangoproject.com/en/1.10/topics/http/urls/
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.conf.urls.static import static

urlpatterns = [
    url(r'^admin', admin.site.urls),
#    url(r'^kit/', include('kit.urls')),
    url(r'^api/', include('api.urls')),
#    url(r'^mon/', include('mon.urls')),
    url(r'^', include('mon.urls')),
]
