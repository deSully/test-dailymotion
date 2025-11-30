.PHONY: build up  logs

build:
	docker compose build

up:
	docker compose up -d

logs:
	docker compose logs -f app

test:
	docker compose exec app pytest

.PHONY: test lint format mypy check

test:
	docker compose exec app pytest
lint:
	ruff check .

format:
	ruff format .
mypy:
	mypy src

check: lint mypy
	@echo "All checks passed!"
