#!/bin/bash

# 1. Exit immediately if any command fails
set -e

# 2. Apply database migrations
echo "Applying migrations..."
python manage.py migrate

# 3. Start the Celery worker in the background
echo "Starting Celery worker..."
celery -A scholarscope worker -l info --concurrency=2 &

# 4. Start Gunicorn and replace the shell process (exec)
echo "Starting Gunicorn..."
exec gunicorn scholarscope.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2