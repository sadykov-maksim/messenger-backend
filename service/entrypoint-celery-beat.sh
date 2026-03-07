#!/bin/sh
set -e

if [ "${DATABASE}" = "django.db.backends.postgresql" ]; then
  echo "Ожидание службы PostgreSQL..."
  while ! nc -z "${DB_HOST}" "${DB_PORT}"; do
    sleep 0.1
  done
  echo "Сервис PostgreSQL запущен"
fi

exec celery -A backend beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler