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

A small note. If you don't have the ability to create isolated python environments, I would recommend installing `conda` ([here](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)) so you can isolate pooltool from your other business.

**1.** Grab a copy of the codebase.

```bash
cd <A_DIRECTORY_YOU_LIKE>
git clone https://github.com/ekiefl/pooltool.git
cd pooltool
```

**2.** Create a new python environment that uses Python 3.12.4.

If you have `conda`, just run this:

```bash
conda env create -f environment.yml
conda activate pooltool-dev
```

Regardless of how you managed your python environment, please verify you're running `3.12.4`

```bash
$ python
Python 3.12.4 | packaged by Anaconda, Inc. | (main, Jun 18 2024, 10:14:12) [Clang 14.0.6 ] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> exit()
```

**3.** Install poetry, a popular python package/environment manager.

If you created your environment with conda (_e.g._ `conda env create -f environment.yml`), poetry is already part of your `pooltool-dev` environment.

Otherwise, install with

```bash
pip install "poetry>=1.8.3"
```

Verify your installation:

```bash
$ poetry --version
Poetry (version 1.8.3)
```

**4.** Install pooltool.

```bash
poetry install --with=dev,docs
pip install -e .

# Intend to contribute? Install the pre-commit hooks.
# This ensures your code is automatically formatted
# to pooltool's code standards before each commit.
pre-commit install
```

**5.** Test out your installation:

```bash
run-pooltool
```

The game window should appear (escape key to exit).

</details>

## Test

Test your installation by printing the version:

```bash
python -c "import pooltool; print(pooltool.__version__)"
```

If installed from source, output should be `0.0.0`.

Next, it's time to learn about the interface.
