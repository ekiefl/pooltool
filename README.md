<img src="pooltool/logo/logo.png" width="600" />

# Intro

*pooltool* is a sandbox billiards game that emphasizes realistic physics. You can play different types of billiards, experiment with different physics settings, or you can use the API to investigate billiards-related research questions.

# Gallery

<img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_1.png" width="350" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_2.png" width="350" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_3.png" width="350" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_5.png" width="350" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_6.png" width="350" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_7.png" width="350" />

# Blog

I have blogged about every aspect of this project. Read the detailed account [here](https://ekiefl.github.io/projects/pooltool/).

# Installation

Installation instructions vary depending on how you want to interact with pooltool. There are 3 current options: _(1) Installer_, _(2) PIP_, and _(3) Developer_. Read on for descriptions and instructions for each installation method.

### Install option (1): Installer

| Method    | GUI | API | Develop |
|-----------|-----|-----|---------|
| Installer | ✅   | ❌   | ❌       |

This is by far the easiest option. If you want to play and experiment with billiards using the graphical user interface (GUI), this option is for you. You won't have access to the python API, or be able to edit the source code. In other words, this is the non-coding option.

Unfortunately, I haven't sorted out this step yet, but eventually there will be OS-specific installers available for download here. Until then, please follow the PIP or Developer instructions below.

### Install option (2): PIP

| Method    | GUI | API | Develop |
|-----------|-----|-----|---------|
| PIP       | ✅   | ✅   | ❌       |

This installation uses `pip`. With this option, you have access to the python API so that you can code up billiards simulations. You also have command-line access to the GUI.

This installation has been tested with the following python versions:

- Python 3.6.2 |Anaconda, Inc.| (default, Oct  5 2017, 03:00:07)
- Python 3.6.10 |Anaconda, Inc.| (default, May  7 2020, 23:06:31)
- Python 3.8.10 (default, May 19 2021, 11:01:55)
- Python 3.9.0 (default, Nov 15 2020, 06:25:35)
- Python 3.10.0 (default, Nov 10 2021, 11:24:47) [Clang 12.0.0 ] on darwin

With a compatible python version, install via

```python
pip install pooltool-billiards
```

After installing, the GUI can be opened at any time via

```bash
run_pooltool
```

You can also use the API. Here is a small python script that runs a shot simulation and then visualizes the results.

```python
#! /usr/bin/env python

import pooltool as pt

interface = pt.ShotViewer()

table = pt.PocketTable()
balls = pt.get_nine_ball_rack(table, ordered=True)
cue = pt.Cue(cueing_ball=balls['cue'])

# Aim at the head ball then strike the cue ball
cue.aim_at_ball(balls['1'])
cue.strike(V0=8)

# Evolve the shot
shot = pt.System(cue=cue, table=table, balls=balls)
shot.simulate(continuize=True)

interface.show(shot)
```

I haven't spent much time on the API yet but hopefully you get the idea.

### Install option (3): Developer

| Method    | GUI | API | Develop |
|-----------|-----|-----|---------|
| Developer | ✅   | ✅   | ✅       |

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
pip install -r requirements_developer.txt
```

In contrast to `requirements.txt`, `requirements_developer.txt` includes some additional convenience modules.

**(iv)** test out your installation:

```bash
python run_pooltool
```

The game window should appear (escape key to exit).

**(v)** if you used a conda environment that you named `pooltool`, create this script that runs whenever the conda environment is activated. This script modifies `$PATH` and `$PYTHONPATH` so that python knows where to find pooltool libraries and the shell knows where to find the pooltool binary. **These path modifications live safely inside the pooltool conda environment, and do not propagate into your global
environment**:

```
mkdir -p ${CONDA_PREFIX}/etc/conda/activate.d
cat <<EOF >${CONDA_PREFIX}/etc/conda/activate.d/pooltool.sh
export PYTHONPATH=\$PYTHONPATH:$(pwd)
export PATH=\$PATH:$(pwd)
EOF
```

The next time you activate your conda environment (`conda activate pooltool`), `run_pooltool` is now a binary
that can be run anywhere in your filesystem whenever you are in the `pooltool` conda environment. Test it out:

```
conda activate pooltool
cd ~
run_pooltool
```

