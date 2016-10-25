from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^factories$', views.factories, name='factories'),
    url(r'^factories/(?P<id>\S*)$', views.factory, name='factory'),
    url(r'^jobs$', views.jobs, name='jobs'),
    url(r'^jobs/(?P<id>\S*)$', views.job, name='job'),
    url(r'^labels$', views.labels, name='labels'),
    url(r'^labels/(?P<id>\S*)$', views.label, name='label'),
]
