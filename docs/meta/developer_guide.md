## Developer Guide

The document provides resources for current/prospective pooltool developers.

### Development environment setup

For complete installation instructions, please refer to the [Installation Guide](../getting_started/install.md). Follow the "From source" section.

After installation, make sure to install the pre-commit hooks, which ensure your code adheres to the project's style guidelines:

```bash
pre-commit install
```

This will automatically check and format your code when you make commits.

### Development workflow

#### Common Make commands

The project includes a Makefile with common commands to streamline development:

**Documentation:**
```bash
make docs                 # Build and view documentation
make live                 # Live preview of docs with auto-refresh
make notebooks            # Execute and update notebooks in docs
make docs-with-notebooks  # Build docs including notebook execution
```

**Code quality:**
```bash
make lint                 # Run linting and fix issues
make lint-check           # Check linting without fixing
make format               # Format code
make format-check         # Check formatting without fixing
make typecheck            # Run type checking
```

**Testing:**
```bash
make test                 # Run all tests
make test-coverage        # Run tests with coverage report
```

**Building and publishing:**
```bash
make clean                # Clean build artifacts
make build                # Build package distribution
```

#### Pre-commit hooks

Pre-commit hooks ensure that code formatting and linting are checked before each commit. These hooks run automatically when you commit code if you've installed them with `pre-commit install`.

The pre-commit configuration in pooltool includes:
- Code formatting (using Ruff)
- Linting checks (using Ruff)
- Type checking (using Pyright)
- Running tests (using Pytest)

If a hook fails, the commit will be aborted. You can fix the issues and try committing again. Sometimes the hooks will automatically fix issues (like formatting), in which case you'll need to stage those changes before committing again.

### Code style and formatting

#### Python code style

* Linting and formatting is handled by [Ruff](https://github.com/astral-sh/ruff).
* Type hints are highly appreciated for all functions and methods

#### Docstring conventions

Pooltool uses Google-style docstrings. Here's an example of the expected format:

```python
def function_name(arg1: str, arg2: int) -> list[str]:
    """Brief description of the function.
    
    More detailed description that can span multiple lines.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
            
    Returns:
        list[str]:
            Description of the return value
        
    Raises:
        ExceptionType: Description of when this exception is raised
        
    Notes:
        Additional information about implementation details
        
    Example:
        >>> code_example
        expected_output
        
    See Also:
        - related_function: Description of how it's related
    """
```

#### Type checking

The project uses [pyright](https://github.com/microsoft/pyright) for static type checking. Type annotations should be used for all function parameters, return values, and class attributes. The type checking configuration is in `pyrightconfig.ci.json`.

### Testing

Pooltool uses [pytest](https://docs.pytest.org/en/stable/) for testing. Tests should be written for all new features and bug fixes.

#### Writing tests

- Tests are located in the `tests/` directory
- Test files should be named `test_*.py`
- Test functions should be named `test_*`

#### Running tests

```bash
# Run all tests
make test

# Run a specific test file
pytest tests/path/to/test_file.py

# Run a specific test
pytest -k test_function_name
```

### Documentation

* Documentation is written in Markdown and built using Sphinx with MyST parser. The documentation is hosted on Read the Docs.
* The API reference is automatically generated from docstrings.
* Examples are provided as Jupyter notebooks in the `docs/examples/` directory.

Commands for building documentation:

```bash
# Build documentation
make docs

# Live preview with auto-reload (recommended for development)
make docs-live

# Execute notebooks, then build docs
make docs-with-notebooks
```

#### Cross-referencing examples

The following shows examples and information for cross-referencing from source → target.

##### Markdown → Python

* {py:meth}`pooltool.objects.Cue.set_state` (text = hyperlink)
* {py:mod}`top-level API <pooltool>`
* {py:class}`System <pooltool.system.System>`

To add an inlaid dropdown signature:

:::{admonition} Admonition Title (e.g. "Physics Engine")
:class: dropdown

Add optional text here

```{eval-rst}
.. autoclass:: pooltool.physics.PhysicsEngine
    :noindex:
```
:::

##### Markdown → Markdown/Jupyter

To cross-reference other pages use **relative paths**. [This takes you to the 30 Degree Rule example](../examples/30_degree_rule.ipynb). Technically, the extension can be ommitted, but since cross-referencing in Jupyter notebooks requires the extension (see below), for consistency please keep the extension.

##### Docstrings → Python

When referencing objects in the same module, simply provide their name:

```rst
:class:`LinearCushionSegment`
:attr:`contains`
:func:`continuize`
```

When referencing from a different module, use the object reference with the lowest level API. As an example, consider `Ball` and its various references:

```python
pooltool.Ball
pooltool.objects.Ball
pooltool.objects.ball.datatypes.Ball
```

`Ball` is defined as `pooltool.objects.ball.datatypes.Ball`, but `pooltool.objects.ball.datatypes` isn't part of the API. `pooltool.Ball` is in the API but it's also referenced as `pooltool.objects.Ball`. Since that has a lower reference, it is the preferred reference. To see which subpackages are part of the API, see what's imported in `pooltool/__init__.py`.

##### Docstrings → Markdown/Jupyter

You can cross-reference document pages with the `:doc:` directive. For example,

```rst
:doc:`Table Specification </resources/table_specs>`
```

##### Jupyter → Python

It's a bit tricky. The working formula is:

```markdown
[Text](../autoapi/{MODULE_PATH}/index.rst#{FULL_OBJECT_DESCRIPTOR})
```

For example, to link to the Table object,

```markdown
[Table](../autoapi/pooltool/objects/index.rst#pooltool.objects.table)
```

##### Jupyter → Markdown/Jupyter

To cross-reference other pages use relative paths:

```markdown
[Straight shot example](./straight_shot.ipynb)
```

Providing the file extension is required.

### Examples gallery

The Examples gallery is a key part of the documentation, consisting of Jupyter notebooks that demonstrate various aspects of pooltool. These notebooks are located in the `docs/examples/` directory.

To add a new example to the gallery:

1. Create a new Jupyter notebook in the `docs/examples/` directory
2. Follow the naming convention of existing examples (descriptive, with underscores)
3. Include a clear title and description at the top of the notebook
5. Add assets (images, etc.) to the `docs/examples/assets/your_example_name/` directory if needed
6. Update the `docs/examples/index.md` file to include your new example
7. Run `make docs-with-notebooks` to build the documentation with your new example

## Pull request workflow

1. **Fork the repository** and create a branch from `main`
2. **Develop your feature or fix** on your branch
3. **Ensure all tests pass** by running `make test`
4. **Format your code** with `make format` and `make lint`
5. **Check types** with `make typecheck`
6. **Push your changes** to your fork
7. **Create a pull request** to the main pooltool repository
