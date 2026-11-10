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

.PHONY: format
format:
	uv run ruff format .
	uv run ruff check --fix-only .

.PHONY: lint
lint:
	uv run ruff format --check .
	uv run ruff check .

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
	NUMBA_DISABLE_JIT=0 uv run pytest --cov=pooltool --cov-report=
	# Trace the kernel source in Python after running the native suite.
	NUMBA_DISABLE_JIT=1 uv run coverage run --append --context=compiled-fp64-interpreted \
		--source=pooltool/evolution/event_based/compiled_fp64 \
		-m pytest tests/evolution/event_based/test_compiled_fp64.py
	uv run coverage xml
	uv run coverage report

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
