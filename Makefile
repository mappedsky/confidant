# bash needed for pipefail
SHELL := /bin/bash

clean:
	find . -name "*.pyc" -delete

up:
	docker compose up

down:
	docker compose down

drop_db:
	docker compose stop dynamodb
	docker compose run --rm --no-deps --entrypoint sh dynamodb -c \
		'rm -rf /home/dynamodblocal/data/*'

docker_build: clean
	DOCKER_BUILDKIT=0 docker build -t mappedsky/confidant .

docker_test: docker_build docker_test_unit docker_test_integration down

docker_test_unit:
	docker compose run --rm --no-deps confidant make test_unit

docker_test_integration:
	docker compose run --rm confidant make test_integration

actions_test_integration:
	docker compose -f docker-compose.yml -f docker-compose.integration.yml run confidant bash /srv/confidant/actions_run_integration.sh

test: test_unit test_integration

test_integration: clean
	mkdir -p build
	pipenv run pytest --strict tests/integration

test_unit: clean
	mkdir -p build
	pipenv run pytest --strict --junitxml=build/unit.xml --cov=confidant --cov-report=html --cov-report=xml --cov-report=term --no-cov-on-fail tests/unit

.PHONY: compile_deps # Update Pipfile.lock
compile_deps:
	pipenv lock

.PHONY: drop_db

.PHONY: docs
docs:
	./docs/build.sh
