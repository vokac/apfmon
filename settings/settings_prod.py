DEBUG = False

SERVER_EMAIL = 'atl@py-front.lancs.ac.uk'

ADMINS = (
#    ('Peter Love', 'p.love@lancaster.ac.uk'),
    ('Peter Love', 'atl@py-front.lancs.ac.uk'),
    ('Peter Love', 'love@hep.lancs.ac.uk'),
)

MANAGERS = ADMINS

ALLOWED_HOSTS = [ 'apfmon.lancs.ac.uk', 'py-front.lancs.ac.uk' ]

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

RAVEN_CONFIG = {
    'dsn': 'https://88a1199737b44ad69ba066601bdf5af1:06e55c48008a4cafbd073da5d882f430@app.getsentry.com/23977',
}
