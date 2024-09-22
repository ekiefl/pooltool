# Load environment variables from the `.env` file if it exists.
ifneq (,$(wildcard .env))
    include .env
endif

.PHONY: docs
docs:
	$(MAKE) -C docs/ clean-and-build-html
	$(MAKE) -C docs/ view-html

.PHONY: clean
clean:
	rm -rf dist

.PHONY: build
build: clean
	poetry build

# Note: `poetry` does not appear to read the `POETRY_PYPI_TOKEN_<NAME>` environment variable,
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
