"""Constants

Notes:
    - **Developer note**: This should really be dissolved into config and motion state
      sections of code
"""

import numpy as np

use_numba_cache = True
np.set_printoptions(precision=16, suppress=True)

EPS = np.finfo(float).eps * 100

MIN_DIST = 1e-6
"""The minimum distance between balls."""

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
airborne: int = 5
"""The airborne motion state label

A ball with this motion state is considered airborne. This state exists only in 3D
simulations.

Important:
    This state includes balls at z=R moving downward; the label routes them to
    ball-table detection.
"""
off_table: int = 6
"""The off-table motion state label

A ball with this motion state has left the playing surface by flying over the cushions.
It takes part in no further physics. Its position is frozen where it crossed the table
boundary and its velocity and angular velocity are zero. This state exists only in 3D
simulations.
"""

state_dict: dict[int, str] = {
    0: "stationary",
    1: "spinning",
    2: "sliding",
    3: "rolling",
    4: "pocketed",
    5: "airborne",
    6: "off_table",
}

on_table = {stationary, spinning, sliding, rolling}
nontranslating = {stationary, spinning, pocketed, off_table}
out_of_play = {pocketed, off_table}
energetic = {spinning, sliding, rolling, airborne}
