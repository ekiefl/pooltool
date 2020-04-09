#! /usr/bin/env python

from psim import *
import numpy as np

if __name__ == '__main__':
    s = ShotSimulation()
    s.setup_test()
    s.start()
