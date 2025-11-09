.PHONY: help install install-dev test test-verbose lint format type-check clean build docs

# Default target
help:
	@echo "Prom-Tools Development Commands:"
	@echo ""
	@echo "  install       Install the package"
	@echo "  install-dev   Install with development dependencies"
	@echo "  test          Run tests"
	@echo "  test-verbose  Run tests with verbose output"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code with black and isort"
	@echo "  type-check    Run type checking with mypy"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build the package"
	@echo "  docs          Generate documentation"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing TODO: implement tests
test:
	python -m pytest tests -v

# Testing TODO: implement tests
test-verbose:
	python -m pytest tests -v

# Testing TODO: implement tests
test-cov:
	python -m pytest tests --cov=src/prom_tools --cov-report=html --cov-report=term

# Code quality TODO: implement linting
lint:
	flake8 src/ tests/
	mypy src/

# Code quality TODO: implement linting
format:
	black src/ tests/
	isort src/ tests/

# Code quality TODO: implement linting
format-check:
	black --check src/ tests/
	isort --check-only src/ tests/

# Code quality TODO: implement linting
type-check:
	mypy src/

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Building
build: clean
	python -m build

# Development workflow
dev-setup: install-dev
	@echo "Development environment set up!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make lint' to check code quality"

# Run examples
run-examples:
	python -m examples.basic_usage

run-monitoring:
	python -m examples.monitoring_automation

# Documentation
docs:
	@echo "Documentation generation not implemented yet"
	@echo "Consider using mkdocs or sphinx for documentation"

# Release
patch-release:
	bump2version patch
	make build

minor-release:
	bump2version minor
	make build

major-release:
	bump2version major
	make build

# Development server (if you have a local dev environment)
dev-prometheus:
	@echo "Starting Prometheus on http://localhost:9090"
	@echo "Make sure you have Prometheus installed"
	# prometheus --config.file=examples/prometheus.yml

dev-grafana:
	@echo "Starting Grafana on http://localhost:3000"
	@echo "Make sure you have Grafana installed"
	# grafana-server --config=examples/grafana.ini