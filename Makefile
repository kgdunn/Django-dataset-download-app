SHELL := /bin/bash

debug:
	python manage.py collectstatic --no-input
	python manage.py migrate
	python manage.py createcachetable
	python manage.py runserver 8080 --nostatic

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
	python -m pip install --upgrade --force-reinstall pip
	conda install -c conda-forge pre-commit --yes
	python -m pip install --upgrade --prefer-binary --no-warn-script-location --use-deprecated=legacy-resolver -r requirements.txt
	pre-commit install
	# Builds the cache, if it doesn't exist already
	git add .pre-commit-config.yaml
	pre-commit
	pre-commit autoupdate
