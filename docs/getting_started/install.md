# Installation

You're just a few seconds away from exploring the interactive interface.

```{figure} ../_assets/gallery_6.jpg
---
height: 300px
---
```

```{figure} ../_assets/gallery_7.jpg
---
height: 300px
---
```

## Requirements

Pooltool is compatible with Python >=3.8 and has been explicitly tested with the following versions:

- Python 3.8.10 (default, May 19 2021, 11:01:55)
- Python 3.9.0 (default, Nov 15 2020, 06:25:35)
- Python 3.10.0 (default, Nov 10 2021, 11:24:47) [Clang 12.0.0 ] on darwin

## Install option (1): pip

| GUI | API | Develop |
|-----|-----|---------|
| ✅  | ✅  | ❌      |

<details><summary style="font-style: italic;">[Click to expand/collapse]</summary>


With a compatible python version, install via

```python
pip install pooltool-billiards
```

**NOTE**: If you're on Linux or Windows, you must _also_ run this:

```python
pip uninstall panda3d -y
pip install --pre --extra-index-url https://archive.panda3d.org/ panda3d
```

</details>

## Install option (2): developer

| GUI | API | Develop |
|-----|-----|---------|
| ✅  | ✅  | ✅      |

<details><summary style="font-style: italic;">[Click to expand/collapse]</summary>

If you want to develop for pooltool, have access to the most up-to-date version of the codebase, or modify the code to your liking, this is for you.

A small note. If you don't have the ability to create isolated python environments, I would recommend installing `conda` ([here](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)) so you can isolate pooltool from your other business.

**(i)** Grab a copy of the codebase.

```bash
cd <A_DIRECTORY_YOU_LIKE>
git clone https://github.com/ekiefl/pooltool.git
cd pooltool
```

**(ii)** Create a new python environment that uses Python 3.8.10.

If you have `conda`, just run this:

```bash
conda env create -f environment.yml
conda activate pooltool
```

Regardless of how you managed your python environment, please verify you're running `3.8.10`

```bash
$ python
Python 3.8.10 (default, May 19 2021, 11:01:55)
[Clang 10.0.0 ] :: Anaconda, Inc. on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> exit()
```

**(iii)** Install poetry, a popular python package/environment manager.

If you created your environment with conda, you've already installed poetry.

Otherwise, install with

```bash
pip install poetry
```

Verify your installation:

```bash
$ poetry --version
Poetry (version 1.8.3)
```

**(iv)** Install pooltool.

```bash
poetry install
pip install -e .
```

**(v)** install the pre-commit hooks:

This will automatically format your code according to the pooltool standard whenever you commit.

```
pre-commit install
```

**(vi)** test out your installation:

```bash
run-pooltool
```

The game window should appear (escape key to exit).

</details>

## Next

Test your installation by printing the version:

```bash
$ python -c "import pooltool; print(pooltool.__version__)"
0.2.2.1-dev
```

Next, it's time to learn about the interface.
