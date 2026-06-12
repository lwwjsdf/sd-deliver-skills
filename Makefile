.PHONY: test test-unit test-integration test-plugin validate fmt cov

# Run all tests except integration tests (default)
test:
	python3 -m pytest -v -m "not integration"

# Run only unit tests
test-unit:
	python3 -m pytest -v -m unit

# Run integration tests (requires external services)
test-integration:
	python3 -m pytest -v -m integration

# Run tests for a specific plugin: make test-plugin PLUGIN=sd-tracking-pipeline
test-plugin:
	@if [ -z "$(PLUGIN)" ]; then \
		echo "Usage: make test-plugin PLUGIN=sd-tracking-pipeline"; \
		exit 1; \
	fi
	python3 -m pytest $(PLUGIN)/tests/ -v

# Validate plugin structure and test coverage
validate:
	python3 validate_plugins.py --check-tests

# Run coverage report (requires pytest-cov)
cov:
	python3 -m pytest -m "not integration" --cov=. --cov-report=term-missing --cov-report=html

# Format Python code (requires black)
fmt:
	python3 -m black sd-*/scripts/ sd-*/tests/ validate_plugins.py conftest.py
