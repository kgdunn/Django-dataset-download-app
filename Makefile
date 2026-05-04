SHELL := /bin/bash

.PHONY: install migrate collectstatic test lint debug docker-up docker-down clean sri

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

sri:
	@# Compute SRI hashes for the two CDN <script> tags in the templates.
	@# Run this on a network-connected machine, then paste the printed
	@# `integrity="sha384-..."` values into base.html (echarts) and
	@# dataset_info.html (mathjax). See docs/SECURITY.md issue K.
	@set -e ; \
	tmp=$$(mktemp -d) ; \
	for url in \
	    "https://cdn.jsdelivr.net/npm/mathjax@2.7.9/MathJax.js" \
	    "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js" ; do \
	    name=$$(basename "$$url") ; \
	    curl -fsSL -o "$$tmp/$$name" "$$url" ; \
	    hash="sha384-$$(openssl dgst -sha384 -binary "$$tmp/$$name" | openssl base64 -A)" ; \
	    echo "$$url" ; \
	    echo "  integrity=\"$$hash\"" ; \
	    echo ; \
	done ; \
	rm -rf "$$tmp"

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
