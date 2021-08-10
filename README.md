<img src="logo/logo.png" width="300" />

# Intro

*pooltool* is a sandbox billiards game that emphasizes realistic physics. You can play any form of billiards, experiment with different physics settings, or you use the API to investigate billiards-related research questions.

# This project is in pre-alpha

Use at your own risk.

# Blog

A blog dedicated to the development of this project can be found on [my website](https://ekiefl.github.io/projects/pooltool/).


# Installation

The installation instructions assume you have [conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html). conda isn't a requirement for installing, but if you don't want to use it, you're on your own.

Deactivate from any conda environments you are currently in, and then create a new conda environment
called pooltool:

```
conda deactivate
conda create -n pooltool python=3.8.10
conda activate pooltool
```

Verify you're running `3.8.10`

```
$ python
Python 3.8.10 (default, May 19 2021, 11:01:55)
[Clang 10.0.0 ] :: Anaconda, Inc. on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> exit()
```

Install all of the dependencies (these installations are localized to your conda environment):

```
conda install -y numpy
conda install -y -c anaconda psutil
conda install -y scipy
conda install -y pandas
conda install -y -c conda-forge panda3d
conda install -y -c conda-forge colored
pip install pyquaternion
```

Now, its time to fetch a copy of the codebase:

```
git clone https://github.com/ekiefl/pooltool.git
cd pooltool
```

Finally, create a script that runs whenever the conda environment is activated. This script
modifies `$PATH` and `$PYTHONPATH` so that python knows where to find pooltool libraries and the shell knows where to find the pooltool binary. **These path
modifications live safely inside the pooltool conda environment, and do not propagate into your global
environment**:

```
mkdir -p ${CONDA_PREFIX}/etc/conda/activate.d
cat <<EOF >${CONDA_PREFIX}/etc/conda/activate.d/pooltool.sh
export PYTHONPATH=\$PYTHONPATH:$(pwd)
export PATH=\$PATH:$(pwd)/bin
EOF
```

Upon activating your conda environment once more (`conda activate pooltool`), `pooltool` is now a binary
that can be run anywhere in your filesystem whenever you are in the `pooltool` conda environment. Time
to test your installation by starting up pooltool:

```
pooltool
```

