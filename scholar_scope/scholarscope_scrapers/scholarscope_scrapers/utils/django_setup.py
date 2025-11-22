# scholarscope_scrapers/scholarscope_scrapers/utils/django_setup.py
import os
import django
import sys

def setup_django():
    # Go up 4 levels from this file → reaches your Django project root
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    sys.path.append(BASE_DIR)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarscope.settings')  # ← change if needed
    django.setup()