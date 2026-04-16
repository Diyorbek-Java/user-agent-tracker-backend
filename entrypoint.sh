#!/bin/sh
set -e

python manage.py migrate --noinput
exec gunicorn monitoring_system.wsgi:application --bind 0.0.0.0:8000
