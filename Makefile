dev:
	poetry run flask --app page_analyzer:app run

lint:
	poetry run flake8