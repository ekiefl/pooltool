# Load environment variables from the `.env` file if it exists.
ifneq (,$(wildcard .env))
    include .env
endif

# ========================================
# Documentation
# ========================================

.PHONY: notebooks
notebooks:
	uv run jupyter nbconvert --to notebook --execute --inplace docs/examples/*.ipynb

.PHONY: docs
docs:
	$(MAKE) -C docs/ clean-and-build-html
	$(MAKE) -C docs/ view-html

.PHONY: docs-live
docs-live:
	$(MAKE) -C docs/ clean-and-build-html
	$(MAKE) -C docs/ live

.PHONY: docs-with-notebooks
docs-with-notebooks: notebooks docs

# ========================================
# Linting, Formatting, and Type Checking
# ========================================

.PHONY: lint
lint:
	uv run ruff check . --fix
	uv run ruff format --check .

.PHONY: lint-check
lint-check:
	uv run ruff check . --verbose --diff

.PHONY: format
format:
	uv run ruff format .

.PHONY: format-check
format-check:
	uv run ruff format . --check --verbose --diff

.PHONY: typecheck
typecheck:
	uv run pyright --project ./pyrightconfig.ci.json

# ========================================
# Testing
# ========================================

.PHONY: test
test:
	uv run pytest

.PHONY: test-coverage
test-coverage:
	uv run pytest --cov=pooltool --cov-report=xml --cov-report=term

# ========================================
# Build and Publish
# ========================================

.PHONY: clean
clean:
	rm -rf dist

.PHONY: build
build: clean
	uv build

.PHONY: build-and-test-publish
build-and-test-publish: build
	uv publish \
		--publish-url https://test.pypi.org/legacy/ \
		--token ${UV_PUBLISH_TOKEN_TEST}

.PHONY: build-and-publish
build-and-publish: build
	uv publish \
		--token ${UV_PUBLISH_TOKEN}
