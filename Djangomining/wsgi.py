import os
import sys

# Set the path to your project directory (تغییر مسیر به پروژه خود)
sys.path.insert(0, '/home/coinbxhb/mining')

# Set the DJANGO_SETTINGS_MODULE to point to your settings file
os.environ['DJANGO_SETTINGS_MODULE'] = 'Djangomining.settings'

# Import and set up the WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
