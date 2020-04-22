#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.engine as engine
import psim.physics as physics
import psim.ani.animate as animate

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

        event = engine.Event(None, None, 0)

        sim.timestamp(0)
        while event.tau < np.inf:
            event = sim.get_next_event()
            sim.evolve(dt=event.tau, event=event)

        sim.continuize(0.05)

        ani = animate.AnimateShot(sim, size=size)
        ani.start()


    # -----------------------------------------------------------------

    if args.choice == 'ani':
        for t in np.diff(np.arange(0, 5, 0.033)):
            sim.evolve(t)

        ani = animate.AnimateShot(sim, size=size)
        ani.start()





