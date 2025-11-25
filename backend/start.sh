#!/bin/bash
echo "Running migrations..."
python manage.py migrate

echo "Starting Django server..."
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
