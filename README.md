<img src="pooltool/logo/logo.png" width="600" />

# Intro

*pooltool* is a sandbox billiards game that emphasizes realistic physics. You can play different types of billiards, experiment with different physics settings, or you use the API to investigate billiards-related research questions.

# Gallery

<img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_1.png" width="300" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_2.png" width="300" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_3.png" width="300" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_5.png" width="300" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_6.png" width="300" /><img src="https://ekiefl.github.io/images/pooltool/pooltool-graphics/gallery_7.png" width="300" />

# Blog

I have blogged about every aspect of this project. Read the detailed account [here](https://ekiefl.github.io/projects/pooltool/).

# Installation

Installation instructions vary depending on how you want to interact with pooltool. There are 3 general categories for installation and they each support the following features:

| Method    | GUI | API | Develop |
|-----------|-----|-----|---------|
| Installer | ✅   | ❎   | ❎       |
| PIP       | ✅   | ✅   | ❎       |
| Developer | ✅   | ✅   | ✅       |

Read on for descriptions and instructions for each installation method.

### Install option #1: Installer

| Method    | GUI | API | Develop |
|-----------|-----|-----|---------|
| Installer | ✅   | ❎   | ❎       |

This is by far the easiest option. If you want to play and experiment with billiards using the graphical user interface (GUI), this option is for you. You won't have access to the python API, or be able to edit the source code. In other words, this is the non-coding option.

Unfortunately, I haven't sorted out this step yet, but eventually there will be OS-specific installers available for download here. Until then, please follow the PIP or Developer instructions below.

### Install option #2: PIP

| Method    | GUI | API | Develop |
|-----------|-----|-----|---------|
| PIP       | ✅   | ✅   | ❎       |

This installation uses `pip`. With this option, you have access to the python API so that you can code up billiards simulations. You also have command-line access to the GUI.

This installation has been tested with the following python versions:

```
Python 3.8.10 (default, May 19 2021, 11:01:55)
```

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
from pooltool.layouts import NineBallRack
from pooltool.evolution import get_shot_evolver
from pooltool.ani.animate import ShotViewer
from pooltool.objects.cue import Cue
from pooltool.objects.ball import Ball
from pooltool.objects.table import PocketTable

# This object will launch the GUI
interface = ShotViewer()

cue = Cue()
table = PocketTable()

diamond = NineBallRack(ordered=True)
diamond.center_by_table(table)
balls = diamond.get_balls_dict()
balls['cue'].rvw[0] = [table.w/2, table.l/4, balls['cue'].R]

# Aim at the head ball then strike the cue ball
cue.set_state(V0=8, theta=0, a=0, b=0, cueing_ball=balls['cue'])
cue.aim_at(balls['1'].rvw[0])
cue.strike()

# Evolve the shot
evolver = get_shot_evolver('event')
shot = evolver(cue=cue, table=table, balls=balls)
shot.simulate(continuize=True)

interface.set_shot(shot)
interface.start()
```

### Install option #3: Developer

| Method    | GUI | API | Develop |
|-----------|-----|-----|---------|
| Developer | ✅   | ✅   | ✅       |

If you want to develop for pooltool, have access to the most up-to-date version of the codebase, or modify the code to your liking, this is for you.

A small note. If you don't have the ability to create isolated python environments, I would recommend installing `conda` ([here](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)) so you can isolate pooltool from your other business.

**(i)**, create a new, python environment that uses Python 3.8.10.

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

**(ii)**, grab the codebase:

```bash
cd <A_DIRECTORY_YOU_LIKE>
git clone https://github.com/ekiefl/pooltool.git
cd pooltool
```

**(iii)**, install the dependencies:

```bash
pip install -r requirements_developer.txt
```

In contrast to `requirements.txt`, `requirements_developer.txt` includes some additional convenience modules.

**(iv)**, test out your installation:

```bash
python run_pooltool
```

The game window should appear (escape key to exit).

**(v optional)**, if you used a conda environment that you named `pooltool`, create this script that runs whenever the conda environment is activated. This script modifies `$PATH` and `$PYTHONPATH` so that python knows where to find pooltool libraries and the shell knows where to find the pooltool binary. **These path modifications live safely inside the pooltool conda environment, and do not propagate into your global
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

