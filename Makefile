.PHONY: build up  logs

build:
	docker compose build

up:
	docker compose up -d

logs:
	docker compose logs -f app

test:
	docker compose exec app pytest

.PHONY: test lint format check

test:
	docker compose exec app pytest
lint:
	ruff check .

format:
	ruff format .