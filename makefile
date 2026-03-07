COMPOSE=docker compose
COMPOSE_FILE=docker-compose.staging.yml
COMPOSE_PROD_FILE=docker-compose.staging.yml

SERVICE=web
MANAGE=python manage.py

version:
	@echo "v1.0.0"

.PHONY: help up down restart logs ps build shell

help:
	@echo "Available commands:"
	@echo "  make up              - Start containers"
	@echo "  make down            - Stop containers"
	@echo "  make restart         - Restart containers"
	@echo "  make build           - Build containers"
	@echo "  make logs            - Show logs"
	@echo "  make ps              - Show containers"
	@echo "  make shell           - Enter web container shell"

ifeq (logs,$(firstword $(MAKECMDGOALS)))
  LOG_TARGET := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(LOG_TARGET):;@:)
endif

logs:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f $(LOG_TARGET)

up:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

down:
	$(COMPOSE) -f $(COMPOSE_FILE) down

restart:
	make down
	make up

build:
	$(COMPOSE) -f $(COMPOSE_FILE) build


ps:
	$(COMPOSE) -f $(COMPOSE_FILE) ps

shell:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) sh

.PHONY: migrate makemigrations createsuperuser shell_plus collectstatic test

migrate:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) $(MANAGE) migrate

makemigrations:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) $(MANAGE) makemigrations

createsuperuser:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) $(MANAGE) createsuperuser

shell_plus:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) $(MANAGE) shell

collectstatic:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) $(MANAGE) collectstatic --noinput

test:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) $(MANAGE) test


.PHONY: lint format

lint:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) flake8

format:
	$(COMPOSE) -f $(COMPOSE_FILE) exec $(SERVICE) black .

.PHONY: docker-clean docker-nuke

docker-clean:
	docker system prune -f

docker-nuke:
	docker stop $$(docker ps -aq) || true
	docker rm -f $$(docker ps -aq) || true
	docker rmi -f $$(docker images -aq) || true
	docker volume rm $$(docker volume ls -q) || true
	docker network rm $$(docker network ls -q) || true
	docker builder prune -a -f
	docker system prune -a --volumes -f


.PHONY: prod-up prod-down prod-logs

prod-up:
	$(COMPOSE) -f $(COMPOSE_PROD_FILE) up -d

prod-down:
	$(COMPOSE) -f $(COMPOSE_PROD_FILE) down

prod-logs:
	$(COMPOSE) -f $(COMPOSE_PROD_FILE) logs -f
