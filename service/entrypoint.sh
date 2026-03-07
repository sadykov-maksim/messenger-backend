#!/bin/sh
set -e

if [ "${DATABASE}" = "django.db.backends.postgresql" ]; then
  echo "Ожидание службы PostgreSQL..."
  while ! nc -z "${DB_HOST}" "${DB_PORT}"; do
    sleep 0.1
  done
  echo "Сервис PostgreSQL запущен"
fi

python manage.py makemigrations
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput --username "$DJANGO_SUPERUSER_USERNAME" || true
fi

exec gunicorn --certfile=/etc/certificates/avocado-messenger.pem --keyfile=/etc/certificates/avocado-messenger.key --bind 0.0.0.0:443 --timeout 3000 backend.wsgi:application