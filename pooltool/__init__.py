"""Constants and other

All units are SI unless otherwise stated.
"""

__version__ = '0.1'

import pooltool.utils as utils
import pooltool.ani.utils as autils

from .constants import *

import numpy as np
np.set_printoptions(precision=10, suppress=True)
#tol = np.finfo(np.float).eps * 100
tol = 1e-12

# Ball states
stationary=0
spinning=1
sliding=2
rolling=3
pocketed=4

state_dict = {
    0: 'stationary',
    1: 'spinning',
    2: 'sliding',
    3: 'rolling',
    4: 'pocketed',
}

nontranslating = [stationary, spinning, pocketed]

