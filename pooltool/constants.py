#! /usr/bin/env python
"""Constants

Notes:
    - **Developer note**: This should really be dissolved into config and motion state
      sections of code
"""

from typing import Dict

import numpy as np

use_numba_cache = True
np.set_printoptions(precision=16, suppress=True)

EPS = np.finfo(float).eps * 100
EPS_SPACE = 1e-9

# Ball states
stationary: int = 0
"""The stationary motion state label

A ball with this motion state is both motionless and not in a pocket.
"""
spinning: int = 1
"""The spinning motion state label

A ball with this motion state is spinning in place.
"""
sliding: int = 2
"""The sliding motion state label

A ball with this motion state is sliding. For details on what this means precisely, see
this `blog <https://ekiefl.github.io/2020/04/24/pooltool-theory/#case-4-sliding>`_.
"""
rolling: int = 3
"""The rolling motion state label

A ball with this motion state is rolling. For details on what this means precisely, see
this `blog <https://ekiefl.github.io/2020/04/24/pooltool-theory/#case-3-rolling>`_.
"""
pocketed: int = 4
"""The pocketed motion state label

A ball with this motion state is in a pocket.
"""

state_dict: Dict[int, str] = {
    0: "stationary",
    1: "spinning",
    2: "sliding",
    3: "rolling",
    4: "pocketed",
}

on_table = {stationary, spinning, sliding, rolling}
nontranslating = {stationary, spinning, pocketed}
energetic = {spinning, sliding, rolling}
