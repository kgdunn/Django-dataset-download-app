"""
WSGI config for datasets project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "datasets.settings")

application = get_wsgi_application()


#import logging.handlers
#log_file = logging.getLogger('debug')
#log_file.setLevel(logging.DEBUG)
#fh = logging.handlers.RotatingFileHandler('/var/tmp/wsgi.log', maxBytes=5000000, backupCount=10)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#fh.setFormatter(formatter)
#log_file.addHandler(fh)
#log_file.debug('Starting WSGI')
#import sys
#log_file.debug('PATH = %s' % str(sys.path))
#print('PATH = %s' % str(sys.path))

#from django.core.wsgi import get_wsgi_application

#WSGIPythonPath    /var/django/datasets:./anaconda3/lib/python3.4/site-packages


#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "datasets.settings")

#application = get_wsgi_application()
