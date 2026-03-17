#!/bin/bash
# Apply database migrations securely
python manage.py migrate

celery -A scholarscope worker -l info &

# Start the Django web server
gunicorn scholarscope.wsgi:application