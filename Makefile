PORT ?= 8000

dev:
	poetry run flask --app page_analyzer:app run

lint:
	poetry run flake8


start:
	poetry run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app