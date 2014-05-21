# This is a sample settings_local.py file. To use it, do:
#
# 1. cp settings_local.py-dist settings_local.py
# 2. edit with your editor
#
# See settings.py and documentation for other things you can configure.

DEBUG = False

SECRET_KEY = '{{ secret_key }}'

DATABASES = {
    'default': {
        # postgresql configuration
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '{{site_name}}',    # db name
        # 'USER': '{{site_name}}',
        # 'PASSWORD': 'richard',
        # 'HOST': 'localhost',
        # 'PORT': ''

    }
}

