# Makefile for EpubSage

.PHONY: help install format test lint typecheck security quality clean

help:
	@echo "EpubSage - Development Commands"
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
	uv run ruff format epubsage
	uv run ruff check --fix epubsage

lint:
	uv run ruff check epubsage

typecheck:
	uv run mypy epubsage

security:
	uv run bandit -r epubsage -q

test:
	PYTHONPATH="$$PWD" uv run pytest tests/ -v

quality: lint typecheck security test
	@echo "All quality checks passed!"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
