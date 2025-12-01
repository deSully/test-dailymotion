.PHONY: build up  logs

build:
	docker compose build

up:
	docker compose up -d

logs:
	docker compose logs -f app

test:
	docker compose exec app pytest

.PHONY: test lint format mypy check clean coverage

test:
	docker compose exec app pytest

coverage:
	docker compose exec app pytest --cov=src --cov-report=term-missing --cov-report=html
	@echo "\nCoverage report generated in htmlcov/index.html"
	
lint:
	ruff check .

format:
	ruff format .

mypy:
	mypy src

check: lint mypy
	@echo "All checks passed!"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	@echo "Cleaned all Python cache files!"
