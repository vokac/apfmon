DEBUG = False

SERVER_EMAIL = 'atl@py-front.lancs.ac.uk'

ADMINS = (
    ('Peter Love', 'love@hep.lancs.ac.uk'),
)

MANAGERS = ADMINS

ALLOWED_HOSTS = [ 'apfmon.lancs.ac.uk', 'py-front.lancs.ac.uk', '148.88.67.83']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': DEFAULTDB_DB,                        # Or path to database file if using sqlite3.
        'USER': DEFAULTDB_USER,               # Not used with sqlite3.
        'PASSWORD': DEFAULTDB_PWD,            # Not used with sqlite3.
        'HOST': 'py-stor',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

CACHES = {
    'default' : {
        'BACKEND'    : 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION'   : 'py-stor.lancs.ac.uk:11211',
        'KEY_PREFIX' : 'prod',
    }
}

GRAPHITE = {
    'host': 'py-heimdallr',
    'port': 8125
}

REDIS = {
    'host': 'py-prod',
    'port': 6379,
}

USE_X_FORWARDED_HOST = True
