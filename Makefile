# Makefile for Al-Warraq

.PHONY: help install format test lint typecheck security quality clean

help:
	@echo "Al-Warraq - Development Commands"
	@echo ""
	@echo "  make install     Install dependencies"
	@echo "  make format      Format code"
	@echo "  make lint        Run linter (ruff)"
	@echo "  make typecheck   Run type checker (mypy)"
	@echo "  make security    Run security scan (bandit)"
	@echo "  make test        Run tests"
	@echo "  make quality     Run all quality checks"
	@echo "  make clean       Remove cache files"

install:
	uv sync

format:
	uv run ruff format al_warraq
	uv run ruff check --fix al_warraq

lint:
	uv run ruff check al_warraq

typecheck:
	uv run mypy al_warraq

security:
	uv run bandit -r al_warraq -q

test:
	PYTHONPATH="$$PWD" uv run pytest tests/ -v

quality: lint typecheck security test
	@echo "All quality checks passed!"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
