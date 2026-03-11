
# path/to/your/proj/src/cfehome/celery.py
import os
from celery import Celery
from decouple import config

# set the default Django settings module for the 'celery' program.
# this is also used in manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarscope.settings')

app = Celery('scholarscope')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# We used CELERY_BROKER_URL in settings.py instead of:
# app.conf.broker_url = ''

# We used CELERY_BEAT_SCHEDULER in settings.py instead of:
# app.conf.beat_scheduler = ''django_celery_beat.schedulers.DatabaseScheduler'

# settings.py or celery.py
CELERY_TASK_ROUTES = {
    'scholarships.draft_single_essay': {'queue': 'llm'},
    'scholarships.draft_essays_batch': {'queue': 'llm'},
    'scholarships.collect_essay_results': {'queue': 'llm'},
}

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {

    # ── Daily 7-day deadline reminder (runs every morning at 8am) ────────────
    "deadline-reminder-7d": {
        "task": "scholarships.send_deadline_reminders",
        "schedule": crontab(hour=8, minute=0),
        "kwargs": {"days_before": 7},
    },

    # ── Daily 3-day deadline reminder (urgent — runs at 9am) ─────────────────
    "deadline-reminder-3d": {
        "task": "scholarships.send_deadline_reminders",
        "schedule": crontab(hour=9, minute=0),
        "kwargs": {"days_before": 3},
    },

    # ── Weekly bulk digest (every Monday at 8am) ──────────────────────────────
    # Catches any pending applications that didn't get a deadline nudge
    "bulk-reminder-weekly": {
        "task": "scholarships.send_bulk_reminders",
        "schedule": crontab(hour=8, minute=0, day_of_week="monday"),
    },

    # ── Weekly renewal check (every Monday at 7am, before bulk digest) ───────
    "renewal-notifications-weekly": {
        "task": "scholarships.send_renewal_notifications",
        "schedule": crontab(hour=7, minute=0, day_of_week="monday"),
    },
}









