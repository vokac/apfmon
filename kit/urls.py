from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^q/$', views.pandaqueues, name='pandaqueues'),
    url(r'^update/$', views.update, name='update'),
]

