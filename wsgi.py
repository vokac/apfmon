#import os
#import sys
#
#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atl.settings")
#
#sys.path.insert(0,'/var/local/django')
#sys.path.insert(0,'/var/local/django/atl')
#
#import django.core.handlers.wsgi
#application = django.core.handlers.wsgi.WSGIHandler()

#activate_this = '/var/local/django/atl/env/bin/activate_this.py'
#execfile(activate_this, dict(__file__=activate_this))
#import sys
#sys.path.insert(0, '/var/local/django/atl')
#
#from django.core.wsgi import get_wsgi_application
#application = get_wsgi_application()


import sys

sys.path.insert(0, '/var/local/django/atl')

import settings

import django.core.management
django.core.management.setup_environ(settings)
utility = django.core.management.ManagementUtility()
command = utility.fetch_command('runserver')

command.validate()

import django.conf
import django.utils

django.utils.translation.activate(django.conf.settings.LANGUAGE_CODE)

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
