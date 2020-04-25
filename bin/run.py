#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.engine as engine
import psim.physics as physics

import numpy as np
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--setup', required=True)
ap.add_argument('-s', '--skip-continuize', action='store_true')
ap.add_argument('-d', '--dimensions', type=int, choices=[2,3], default=2)
args = ap.parse_args()

if __name__ == '__main__':
    sim = engine.ShotSimulation()
    sim.setup_test(args.setup)

    event = engine.Event(None, None, 0)

    sim.timestamp(0)
    while event.tau < np.inf:
        event = sim.get_next_event()
        sim.evolve(dt=event.tau, event=event)

    if not args.skip_continuize:
        sim.continuize(0.05)

    if args.dimensions == 2:
        from psim.ani.animate2d import AnimateShot

        kwargs = {
            'size': 800
        }

    elif args.dimensions == 3:
        from psim.ani.animate3d import AnimateShot

        kwargs = {
        }

    ani = AnimateShot(sim, **kwargs)
    ani.start()
