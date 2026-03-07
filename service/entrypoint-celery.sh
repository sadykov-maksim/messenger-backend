#!/bin/sh
set -e

if [ "${DATABASE}" = "django.db.backends.postgresql" ]; then
  echo "Ожидание службы PostgreSQL..."
  while ! nc -z "${DB_HOST}" "${DB_PORT}"; do
    sleep 0.1
  done
  echo "Сервис PostgreSQL запущен"
fi

exec celery -A backend worker -l info -c 1 --prefetch-multiplier=1