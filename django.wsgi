import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'atl.settings'

sys.path.append('/var/local/django')
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()


#import os
#
#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atl.settings")
#
## This application object is used by the development server
## as well as any WSGI server configured to use this file.
#from django.core.wsgi import get_wsgi_application
#application = get_wsgi_application()
