include .env

# Note: `poetry` does not appear to read the `POETRY_PYPI_TOKEN_<NAME>` environment variable,
# so we need to pass it explicitly in the `publish` command.
.PHONY: test-publish
test-publish:
	echo ${POETRY_PYPI_TOKEN_PYPI_TEST}
	poetry publish \
		--repository pypi-test \
		--username __token__ \
		--password ${POETRY_PYPI_TOKEN_PYPI_TEST}

.PHONY: publish
publish: build
	poetry publish \
		--username __token__ \
		--password ${POETRY_PYPI_TOKEN_PYPI}
