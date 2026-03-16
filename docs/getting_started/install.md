# Installation

Pooltool is available on Linux, Mac, and Windows for the following Python versions:

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pooltool-billiards)

## Using pip

Pooltool is hosted on the [Python Package Index (PyPI)](https://pypi.org/project/pooltool-billiards/) and can be installed with pip.

```{eval-rst}
.. tabs::

   .. tab:: **Linux**

      .. code-block:: bash

         pip install pooltool-billiards --extra-index-url https://archive.panda3d.org/

      (*Providing the Panda3D archive is required until Panda3D v1.11 is released*)

   .. tab:: **MacOS**

      .. code-block:: bash

         pip install pooltool-billiards

   .. tab:: **Windows**

      .. code-block:: bash

         pip install pooltool-billiards --extra-index-url https://archive.panda3d.org/

      (*Providing the Panda3D archive is required until Panda3D v1.11 is released*)
```

## From source

If you want to develop for pooltool, have access to the most up-to-date version of the codebase, or modify the code to your liking, this is for you.

<details><summary style="font-style: italic;">[Click to expand/collapse]</summary>

**1.** Grab a copy of the codebase.

```bash
cd <A_DIRECTORY_YOU_LIKE>
git clone https://github.com/ekiefl/pooltool.git
cd pooltool
```

**2.** Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't already have it.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify your installation:

```bash
$ uv --version
```

**3.** Install pooltool.

```bash
uv sync --group dev --group docs

# Intend to contribute? Install the pre-commit hooks.
# This ensures your code is automatically formatted
# to pooltool's code standards before each commit.
uv run pre-commit install
```

**4.** Test out your installation:

```bash
uv run run-pooltool
```

The game window should appear (escape key to exit).

</details>

## Test

Test your installation by printing the version:

```bash
uv run python -c "import pooltool; print(pooltool.__version__)"
```

Next, check out [The Interface](./interface.md).
