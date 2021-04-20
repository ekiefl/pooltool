"""Constants and other

All units are SI unless otherwise stated.
"""

import numpy as np

np.set_printoptions(precision=10, suppress=True)

__version__ = '0.1'

# Taken from https://billiards.colostate.edu/faq/physics/physical-properties/
g = 9.8 # gravitational constant
M = 0.567 # cue mass
cue_length = 1.4732 # 58 inches
cue_tip_radius = 0.0254/4 # Fake
cue_butt_radius = 0.0254/4 # Fake
m = 0.170097 # ball mass
R = 0.028575 # ball radius
u_s = 0.2 # sliding friction
u_r = 0.01 # rolling friction
u_sp = 10 * 2/5*R/9 # spinning friction
table_length = 1.98 # 9-foot table (100 in x 50 in)
table_width = 1.98/2 # 9-foot table (100 in x 50 in)

rail_width = 0.0635
rail_height = 0.64*2*R
table_edge_width = 0.10
table_height = 0.75
lights_height = 1.1 # relative to playing surface
diamond_size = 0.01

# Ball states
stationary=0
spinning=1
sliding=2
rolling=3

state_dict = {
    0: 'stationary',
    1: 'spinning',
    2: 'sliding',
    3: 'rolling',
}

#tol = np.finfo(np.float).eps * 100
tol = 1e-12
