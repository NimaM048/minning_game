import os
import sys

# مسیر واقعی پروژه Django
sys.path.insert(0, '/home/coinbxhb/minning')

# تنظیمات Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'Djangomining.settings'

# اجرای WSGI
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
