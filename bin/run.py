#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.engine as engine
import psim.physics as physics

import numpy as np
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--choice', required=True, choices=['col', 'ani'])
args = ap.parse_args()

if __name__ == '__main__':
    sim = engine.ShotSimulation()
    sim.setup_test('straight_shot')

    size = 800

    # -----------------------------------------------------------------

    if args.choice == 'col':
        sim.simulate_event_based()

    # -----------------------------------------------------------------

    if args.choice == 'ani':
        sim.simulate_discrete_time()

    sim.animate()





