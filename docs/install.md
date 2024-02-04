# Getting Started

You're just a few seconds away from exploring the interactive interface.

<img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_6.png" width="350" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_7.png" width="350" />

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

## Install option (2): manual

| GUI | API | Develop |
|-----|-----|---------|
| ✅  | ✅  | ✅      |

<details><summary style="font-style: italic;">[Click to expand/collapse]</summary>

If you want to develop for pooltool, have access to the most up-to-date version of the codebase, or modify the code to your liking, this is for you.

A small note. If you don't have the ability to create isolated python environments, I would recommend installing `conda` ([here](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)) so you can isolate pooltool from your other business.

**(i)** create a new, python environment that uses Python 3.8.10.

With `conda`, you could do the following:

```bash
conda deactivate
conda env remove --name pooltool
conda create -y -n pooltool python=3.8.10
conda activate pooltool
```

Regardless of how you managed your python environment, please verify you're running `3.8.10`

```
$ python
Python 3.8.10 (default, May 19 2021, 11:01:55)
[Clang 10.0.0 ] :: Anaconda, Inc. on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> exit()
```

**(ii)** grab the codebase:

```bash
cd <A_DIRECTORY_YOU_LIKE>
git clone https://github.com/ekiefl/pooltool.git
cd pooltool
```

**(iii)** install the dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

In addition to `requirements.txt`, `requirements-dev.txt` includes some modules required for developement.

**NOTE**: If you're on Linux or Windows, you must _also_ run this:

```python
pip uninstall panda3d -y
pip install --pre --extra-index-url https://archive.panda3d.org/ panda3d
```

(_This is because there is a bug where the mouse moves off of the screen when aiming in the GUI, making you lose mouse control on Linux and Windows. The solution is to install Panda3D v1.11, which is currently unreleased but still installable._)

**(iv)** install the pre-commit hooks:

This will automatically format your code according to the pooltool standard whenever you commit.

```
pre-commit install
```

**(v)** test out your installation:

```bash
python run_pooltool
```

The game window should appear (escape key to exit).

**(vi)** if you used a conda environment that you named `pooltool`, create this script that runs whenever the conda environment is activated. This script modifies `$PATH` and `$PYTHONPATH` so that python knows where to find pooltool libraries and the shell knows where to find the pooltool binary. **These path modifications live safely inside the pooltool conda environment, and do not propagate into your global
environment**:

(_This is a multi-line command. Paste the entire block into your command line prompt._)

```
mkdir -p ${CONDA_PREFIX}/etc/conda/activate.d
cat <<EOF >${CONDA_PREFIX}/etc/conda/activate.d/pooltool.sh
export PYTHONPATH=\$PYTHONPATH:$(pwd)
export PATH=\$PATH:$(pwd)
EOF
```

The next time you activate your conda environment (`conda activate pooltool`), `run_pooltool` (or `run_pooltool.bat` if you're on Windows) is now a binary that can be run anywhere in your filesystem whenever you are in the `pooltool` conda environment. Test it out:
```
conda activate pooltool
cd ~
run_pooltool
```

</details>

## Test installation

After installation, the GUI should be available from the command line:

```bash
run_pooltool
```

Or, if you're on Windows:

```bash
run_pooltool.bat
```

You can also use the API. Here is a small python script that runs a shot simulation and then visualizes the results.

```python
#! /usr/bin/env python

import pooltool as pt

interface = pt.ShotViewer()

# We need a table, some balls, and a cue stick
table = pt.Table.default()
balls = pt.get_nine_ball_rack(table)
cue = pt.Cue(cue_ball_id="cue")

# Wrap it up as a System
shot = pt.System(table=table, balls=balls, cue=cue)

# Aim at the head ball with a strong impact
shot.strike(V0=8, phi=pt.aim.at_ball(shot, "1"))

# Evolve the shot.
pt.simulate(shot, inplace=True)

# Open up the shot in the GUI
interface.show(shot)
```

