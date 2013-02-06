from django.conf.urls.defaults import *

urlpatterns = patterns('atl.api.views',
    (r'^factories$', 'factories'),
    (r'^factories/(?P<id>\S*)$', 'factory'),
    (r'^jobs$', 'jobs'),
    (r'^jobs/(?P<id>\S*)$', 'job'),
    (r'^labels$', 'labels'),
    (r'^labels/(?P<id>\S*)$', 'label'),

)
