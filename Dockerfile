# Этап, на котором выполняются подготовительные действия
FROM python:3.13.1 as builder
LABEL authors="Avocado"

WORKDIR /installer

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt update && \
    apt install -y --no-install-recommends gcc


RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY service/requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt --use-deprecated=legacy-resolver

# Финальный этап
FROM python:3.13.1
LABEL authors="Avocado"


RUN apt update && \
    apt install -y --no-install-recommends netcat-traditional locales gettext \
      libnss3 libgconf-2-4 libasound2 && \
    apt clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY compatibility ./opt/
COPY postgresql ./postgresql/

WORKDIR /service

ENV PATH="/opt/venv/bin:$PATH"
ENV PGSERVICEFILE /postgresql/.pg_service.conf
ENV PGPASSFILE /postgresql/.pgpass

COPY service .
COPY service/entrypoint.sh entrypoint.sh

EXPOSE 443

#ENTRYPOINT ["sh", "-c", "tail -f /dev/null"]
ENTRYPOINT ["sh", "./entrypoint.sh"]