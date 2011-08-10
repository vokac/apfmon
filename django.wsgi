import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'atl.settings'

sys.path.append('/var/local/django')
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
