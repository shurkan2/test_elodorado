COMPOSE = docker compose -f docker-compose.yml -f docker-compose.dev.yml

.PHONY: up up-build down down-all reset stop-celery start-celery ps test create-test-db

up:
	$(COMPOSE) up -d

up-build:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

down-all:
	$(COMPOSE) down -v

reset: down-all up-build

stop-celery:
	$(COMPOSE) stop celery_worker_light celery_worker_heavy celery_beat

start-celery:
	$(COMPOSE) start celery_worker_light celery_worker_heavy celery_beat

ps:
	$(COMPOSE) ps

create-test-db:
	@$(COMPOSE) exec db psql -U app -d retail_network -c "CREATE DATABASE retail_network_test;" 2>/dev/null || true

test: create-test-db
	$(COMPOSE) exec \
		-e TEST_DATABASE_URL=postgres://app:app@db:5432/retail_network_test \
		web python manage.py test --noinput
