.PHONY: install lock run test lint build docker-run

install:
	poetry install

lock:
	poetry lock

run:
	poetry run python -m src.main

test:
	poetry run pytest -v

lint:
	poetry run black src tests
	poetry run isort src tests

build:
	docker build -t yalla-trip .

docker-run:
	docker run --env-file .env -p 8000:8000 yalla-trip
