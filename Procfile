release: /app/.venv/bin/python manage.py migrate && /app/.venv/bin/python manage.py collectstatic --noinput
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT