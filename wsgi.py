activate_this = '/var/local/django/atl/env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import os
import sys

sys.path.insert(0, '/var/local/django/')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atl.settings")

# This application object is used by the development server
# as well as any WSGI server configured to use this file.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

#import sys
#
#sys.path.insert(0, '/var/local/django/atl')
#
#import settings
#
#import django.core.management
#django.core.management.setup_environ(settings)
#utility = django.core.management.ManagementUtility()
#command = utility.fetch_command('runserver')
#
#command.validate()
#
#import django.conf
#import django.utils
#
#django.utils.translation.activate(django.conf.settings.LANGUAGE_CODE)
#
#import django.core.handlers.wsgi
#
#application = django.core.handlers.wsgi.WSGIHandler()
