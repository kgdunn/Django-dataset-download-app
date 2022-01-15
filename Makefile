SHELL := /bin/bash



debug:
	python manage.py collectstatic --no-input
	python manage.py migrate
	python manage.py createcachetable
	python manage.py runserver 8080 --nostatic
