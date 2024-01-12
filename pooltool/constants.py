#! /usr/bin/env python
"""Constants and other

All units are SI unless otherwise stated.
"""

import numpy as np

use_numba_cache = True
np.set_printoptions(precision=16, suppress=True)

EPS = np.finfo(float).eps * 100
EPS_SPACE = 1e-9

# Ball states
stationary = 0
spinning = 1
sliding = 2
rolling = 3
pocketed = 4

state_dict = {
    0: "stationary",
    1: "spinning",
    2: "sliding",
    3: "rolling",
    4: "pocketed",
}

on_table = {stationary, spinning, sliding, rolling}
nontranslating = {stationary, spinning, pocketed}
energetic = {spinning, sliding, rolling}

english_fraction = 0.5000001
