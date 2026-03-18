# bash needed for pipefail
SHELL := /bin/bash

clean:
	find . -name "*.pyc" -delete

up:
	docker compose up

down:
	docker compose down

docker_build: clean
	docker build -t lyft/confidant .

docker_build_frontend:
	docker build -t confidant-frontend -f Dockerfile.frontend .

docker_test: docker_build docker_build_frontend docker_test_unit docker_test_integration docker_test_frontend down

docker_test_unit:
	docker compose run --rm --no-deps confidant make test_unit

docker_test_integration:
	docker compose run --rm confidant make test_integration

actions_test_integration:
	docker compose -f docker-compose.yml -f docker-compose.integration.yml run confidant bash /srv/confidant/actions_run_integration.sh

docker_test_frontend:
	docker run --rm -v $(pwd):/app confidant-frontend bun run test

test: test_unit test_integration test_frontend

test_integration: clean
	mkdir -p build
	pipenv run pytest --strict tests/integration

test_unit: clean
	mkdir -p build
	pipenv run pytest --strict --junitxml=build/unit.xml --cov=confidant --cov-report=html --cov-report=xml --cov-report=term --no-cov-on-fail tests/unit

test_frontend:
	docker run --rm -v $(pwd):/app confidant-frontend bun run build

.PHONY: compile_deps # Update Pipfile.lock
compile_deps:
	pipenv lock

.PHONY: docs
docs:
	./docs/build.sh
