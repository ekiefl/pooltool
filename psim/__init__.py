import numpy as np

np.set_printoptions(precision=3)
np.set_printoptions(suppress=True)

__version__ = '0.1'

# all units are SI. Taken from https://billiards.colostate.edu/faq/physics/physical-properties/

g = 9.8 # gravitational constant
M = 0.567 # cue mass
m = 0.170097 # ball mass
R = 0.028575 # ball radius
u_s = 0.2 # sliding friction
u_r = 0.01 # rolling friction
u_sp = 10 * 2/5*R/9 # spinning friction
table_length = 2.7432 # 9-foot table
table_width = 2.7432/2 # 9-foot table

from psim.engine import *
