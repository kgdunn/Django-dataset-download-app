SHELL := /bin/bash

.PHONY: install migrate collectstatic test lint debug docker-up docker-down clean

install:
	uv sync --dev

migrate:
	uv run python manage.py migrate

collectstatic:
	uv run python manage.py collectstatic --no-input

test:
	uv run pytest

lint:
	uv run pre-commit run --all-files

debug: collectstatic migrate
	uv run python manage.py createcachetable
	uv run python manage.py runserver 8080 --nostatic

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache
	rm -rf static
