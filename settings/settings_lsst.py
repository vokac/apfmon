DEBUG = True

SERVER_EMAIL = 'apfmon@localhost'

ADMINS = (
    ('apfmon', 'apfmon@localhost'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'apfmon.db',                        # Or path to database file if using sqlite3.
        'USER': '',               # Not used with sqlite3.
        'PASSWORD': '',            # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

#CACHES = {
#    'default' : {
#        'BACKEND'    : 'django.core.cache.backends.memcached.MemcachedCache',
#        'LOCATION'   : 'py-stor:11211',
#        'KEY_PREFIX' : 'py-dev',
#    }
#}

APFMONURL = 'http://localhost:8000/api/'
