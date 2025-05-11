# Load environment variables from the `.env` file if it exists.
ifneq (,$(wildcard .env))
    include .env
endif

# ========================================
# Documentation
# ========================================

.PHONY: notebooks
run-notebooks:
	poetry run jupyter nbconvert --to notebook --execute --inplace docs/examples/*.ipynb

.PHONY: docs
docs:
	$(MAKE) -C docs/ clean-and-build-html
	$(MAKE) -C docs/ view-html

.PHONY: docs-with-notebooks
docs-with-notebooks: notebooks docs

# ========================================
# Linting, Formatting, and Type Checking
# ========================================

.PHONY: lint
lint:
	poetry run ruff check . --fix

.PHONY: lint-check
lint-check:
	poetry run ruff check . --verbose --diff

.PHONY: format
format:
	poetry run ruff format .

.PHONY: format-check
format-check:
	poetry run ruff format . --check --verbose --diff

.PHONY: typecheck
typecheck:
	poetry run pyright --project ./pyrightconfig.ci.json

# ========================================
# Testing
# ========================================

.PHONY: test
test:
	poetry run pytest

.PHONY: test-coverage
test-coverage:
	poetry run pytest --cov=pooltool --cov-report=xml --cov-report=term

# ========================================
# Build and Publish
# ========================================

.PHONY: clean
clean:
	rm -rf dist

.PHONY: build
build: clean
	poetry build

# Note: `poetry` does not appear to read the `POETRY_PYPI_TOKEN_<n>` environment variable,
# so we need to pass it explicitly in these publishing commands.
.PHONY: build-and-test-publish
build-and-test-publish: build
	poetry publish \
		--repository pypi-test \
		--username __token__ \
		--password ${POETRY_PYPI_TOKEN_PYPI_TEST}

.PHONY: build-and-publish
build-and-publish: build
	poetry publish \
		--username __token__ \
		--password ${POETRY_PYPI_TOKEN_PYPI}
