.PHONY: help install test clean lint docs dev-setup

help:
	@echo "Modularity - Make Commands"
	@echo "=================================="
	@echo "  make install      Install all dependencies"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run linters"
	@echo "  make clean        Clean build artifacts"
	@echo "  make docs         Build documentation"
	@echo "  make dev-setup    Setup development environment"
	@echo ""

install:
	@echo "Installing all components..."
	cd packages/sdk-python && pip install -e .
	cd packages/registry && pip install -r requirements.txt
	cd packages/cli && pip install -e .
	@echo "✓ Installation complete"

test:
	@echo "Running tests..."
	cd packages/sdk-python && pytest -v
	cd packages/registry && pytest -v
	cd packages/cli && pytest -v
	@echo "✓ All tests passed"

lint:
	@echo "Running linters..."
	cd packages/sdk-python && flake8 .
	cd packages/registry && flake8 .
	cd packages/cli && flake8 .
	@echo "✓ Linting complete"

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Clean complete"

docs:
	@echo "Building documentation..."
	cd docs && mkdocs build
	@echo "✓ Documentation built"

dev-setup:
	@echo "Setting up development environment..."
	pip install pytest flake8 black mypy
	@echo "✓ Development environment ready"
