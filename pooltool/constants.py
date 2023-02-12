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

# Taken from https://billiards.colostate.edu/faq/physics/physical-properties/
g = 9.8  # gravitational constant
m = 0.170097  # ball mass
R = 0.028575  # ball radius
u_s = 0.2  # sliding friction
u_r = 0.01  # rolling friction
u_sp = 10 * 2 / 5 * R / 9  # spinning friction
e_c = 0.85  # cushion coeffiient of restitution
f_c = 0.2  # cushion coeffiient of friction

english_fraction = 0.5
