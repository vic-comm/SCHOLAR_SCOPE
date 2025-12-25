# # scholar_scope/celery.py
# from __future__ import absolute_import, unicode_literals
# import os
# from scholar_scope.celery_app import Celery

# # set default Django settings
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scholar_scope.settings")

# app = Celery("scholar_scope")

# # load task modules from all registered Django apps
# app.config_from_object("django.conf:settings", namespace="CELERY")
# app.autodiscover_tasks()
