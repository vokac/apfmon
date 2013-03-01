venv_django_root = '/var/local/django'
try:
    activate_this = venv_django_root + '/atl/env/bin/activate_this.py'
    execfile(activate_this, dict(__file__=activate_this))

    import os
    import sys

    sys.path.insert(0, venv_django_root)

except IOError: # not running under venv
    import os
    import sys

    newpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, newpath)
    sys.path.insert(0, newpath+"/atl")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atl.settings")
# This application object is used by the development server
# as well as any WSGI server configured to use this file.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

