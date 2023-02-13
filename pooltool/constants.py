#! /usr/bin/env python
"""Constants and other

All units are SI unless otherwise stated.
"""

import numpy as np

numba_cache = True
np.set_printoptions(precision=10, suppress=True)
# tol = np.finfo(np.float).eps * 100
tol = 1e-12

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

nontranslating = {stationary, spinning, pocketed}
energetic = {spinning, sliding, rolling}

english_fraction = 0.5
